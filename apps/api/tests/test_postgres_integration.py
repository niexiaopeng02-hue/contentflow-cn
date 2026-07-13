import os

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import ContentAnalysis, ContentScore, GeneratedContent, Project, SourceContent
from app.schemas import (
    GeneratedContentUpdate,
    ProjectCreate,
    ProjectGenerateRequest,
    RewriteRequest,
)
from app.services.projects import (
    create_content_version,
    create_project,
    delete_project,
    export_project_markdown,
    generate_project,
    get_project_detail,
    list_project_contents,
    retry_project,
)

RAW_TEXT = (
    "Many people learn AI by collecting tools instead of connecting AI to real work. "
    "A better method is to choose one repeated daily problem, use AI to produce a first "
    "draft, review the result, and turn the prompt into a reusable workflow. The value "
    "comes from the workflow and the result, not from a magic tool list."
)


pytestmark = pytest.mark.postgres


@pytest.fixture
async def pg_session() -> AsyncSession:
    database_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")
    engine = create_async_engine(database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        await session.execute(
            text(
                "TRUNCATE users, projects, source_contents, content_analysis, "
                "generated_contents, content_scores RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_migration_and_full_content_flow(
    pg_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    revision = await pg_session.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "20260710_0003"

    project = await create_project(
        pg_session,
        ProjectCreate(
            name="PostgreSQL Runtime Flow",
            category="AI科技",
            source_type="article",
            target_platforms=["xiaohongshu", "douyin", "wechat"],
        ),
    )
    generated = await generate_project(
        pg_session,
        project.id,
        ProjectGenerateRequest(
            title="PostgreSQL Runtime Source",
            raw_text=RAW_TEXT,
            target_platforms=["xiaohongshu", "douyin", "wechat"],
        ),
    )
    assert len(generated.generated_contents) == 3
    detail = await get_project_detail(pg_session, project.id)
    assert detail.status == "completed"
    assert detail.analysis
    assert await count(pg_session, SourceContent) == 1
    assert await count(pg_session, ContentAnalysis) == 1
    assert await count(pg_session, GeneratedContent) == 3
    assert await count(pg_session, ContentScore) == 3

    content = (await list_project_contents(pg_session, project.id, platform="douyin"))[0]
    edited = dict(content.content)
    edited["cta"] = "Tell me which repeated task you want to automate."
    version_two = await create_content_version(
        pg_session,
        content.id,
        GeneratedContentUpdate(content=edited),
    )
    assert version_two.version == 2

    version_three = await create_content_version(
        pg_session,
        content.id,
        RewriteRequest(
            instruction="reduce AI tone",
            target="both",
            instruction_type="reduce_ai_tone",
        ),
        rewrite=True,
    )
    assert version_three.version == 3
    assert version_three.score.ai_risk_level in {"low", "medium", "high"}

    stored_score = await pg_session.scalar(
        select(ContentScore).where(ContentScore.generated_content_id == version_three.id)
    )
    assert stored_score
    assert stored_score.risk_details["ai_risk_level"] == version_three.score.ai_risk_level
    assert isinstance(stored_score.risk_details["risk_reasons"], list)
    assert isinstance(stored_score.risk_details["rewrite_suggestions"], list)

    markdown = await export_project_markdown(pg_session, project.id)
    assert "## xiaohongshu" in markdown
    assert "## douyin" in markdown
    assert "## wechat" in markdown

    retry_project_model = await create_project(pg_session, ProjectCreate(name="PostgreSQL Retry"))
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
    with pytest.raises(HTTPException):
        await generate_project(
            pg_session,
            retry_project_model.id,
            ProjectGenerateRequest(title="Retry Source", raw_text=RAW_TEXT),
        )
    before_retry_sources = await count(pg_session, SourceContent)
    await retry_project(pg_session, retry_project_model.id)
    assert await count(pg_session, SourceContent) == before_retry_sources

    await delete_project(pg_session, project.id)
    assert await pg_session.scalar(select(Project).where(Project.id == project.id)) is None


async def count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count(model.id))))
