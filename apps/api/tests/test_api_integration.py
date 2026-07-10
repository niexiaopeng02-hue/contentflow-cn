import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app

RAW_TEXT = (
    "Many creators learn AI by collecting tools, but the better path is to connect AI "
    "to a repeated work problem. Pick one real task, use AI for the first draft, review "
    "the result manually, and turn the prompt into a reusable workflow. This makes the "
    "improvement come from the process rather than from a magic tool list."
)


@pytest.fixture
async def api_client() -> AsyncClient:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_session():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_api_project_generation_edit_rewrite_and_export(api_client: AsyncClient) -> None:
    create_response = await api_client.post("/api/v1/projects", json={"name": "API Flow"})
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]

    detail_response = await api_client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200

    generate_response = await api_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "title": "API Flow Source",
            "raw_text": RAW_TEXT,
            "target_platforms": ["xiaohongshu", "douyin", "wechat"],
        },
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()["generated_contents"]
    assert len(generated) == 3

    contents_response = await api_client.get(f"/api/v1/projects/{project_id}/contents")
    assert contents_response.status_code == 200
    content = contents_response.json()[0]
    content_id = content["id"]
    updated_payload = dict(content["content"])
    updated_payload["cta"] = "Save this workflow."

    patch_response = await api_client.patch(
        f"/api/v1/generated-contents/{content_id}",
        json={"content": updated_payload},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["version"] == 2

    versions_response = await api_client.get(f"/api/v1/generated-contents/{content_id}/versions")
    assert versions_response.status_code == 200
    assert [item["version"] for item in versions_response.json()] == [1, 2]

    rewrite_response = await api_client.post(
        f"/api/v1/generated-contents/{content_id}/rewrite",
        json={
            "instruction": "reduce AI tone",
            "target": "both",
            "instruction_type": "reduce_ai_tone",
        },
    )
    assert rewrite_response.status_code == 200
    assert rewrite_response.json()["version"] == 3

    export_response = await api_client.get(f"/api/v1/projects/{project_id}/export/markdown")
    assert export_response.status_code == 200
    assert "# API Flow" in export_response.text


@pytest.mark.asyncio
async def test_api_retry_failed_project(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_response = await api_client.post("/api/v1/projects", json={"name": "API Retry"})
    project_id = create_response.json()["id"]

    import app.services.projects as project_service

    real_pipeline = project_service.run_text_pipeline
    calls = 0

    async def flaky_pipeline(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider failure")
        return await real_pipeline(*args, **kwargs)

    monkeypatch.setattr("app.services.projects.run_text_pipeline", flaky_pipeline)
    failed_response = await api_client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"title": "API Retry Source", "raw_text": RAW_TEXT},
    )
    assert failed_response.status_code == 500

    retry_response = await api_client.post(f"/api/v1/projects/{project_id}/retry")
    assert retry_response.status_code == 200
    assert len(retry_response.json()["generated_contents"]) == 3

    rejected_response = await api_client.post(f"/api/v1/projects/{project_id}/retry")
    assert rejected_response.status_code == 400
