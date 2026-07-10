import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import ContentAnalysis, ContentScore, GeneratedContent, SourceContent
from app.repositories import GeneratedContentRepository, ProjectRepository
from app.schemas import (
    GeneratedContentUpdate,
    ProjectCreate,
    ProjectGenerateRequest,
    RewriteRequest,
)
from app.services.projects import (
    create_content_version,
    create_project,
    dashboard_stats,
    export_project_markdown,
    generate_project,
    get_analysis,
    get_project_detail,
    get_version,
    list_project_contents,
    list_projects,
    list_versions,
    retry_project,
)


async def table_count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count(model.id))))


RAW_TEXT = (
    "内容创作者需要把一份长内容拆成多个平台版本。有效流程不是直接改写，"
    "而是先清洗内容、分析主题、提炼核心观点、识别受众，再分别生成小红书、"
    "抖音和公众号内容。这样能保留观点，也能适配不同平台的阅读场景。"
)


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as db:
        yield db
    await engine.dispose()


async def make_completed_project(session: AsyncSession):
    project = await create_project(
        session,
        ProjectCreate(
            name="Lifecycle Test",
            category="内容运营",
            source_type="文章",
            target_platforms=["xiaohongshu", "douyin", "wechat"],
        ),
    )
    response = await generate_project(
        session,
        project.id,
        ProjectGenerateRequest(
            title="Lifecycle Test",
            raw_text=RAW_TEXT,
            target_platforms=["xiaohongshu", "douyin", "wechat"],
        ),
    )
    return project.id, response


@pytest.mark.asyncio
async def test_project_create_and_list(session: AsyncSession) -> None:
    project = await create_project(session, ProjectCreate(name="My Project"))
    projects = await list_projects(session)
    assert project.status == "draft"
    assert [item.id for item in projects] == [project.id]


@pytest.mark.asyncio
async def test_project_detail_after_generation(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    detail = await get_project_detail(session, project_id)
    assert detail.status == "completed"
    assert detail.analysis is not None
    assert detail.source_content is not None


@pytest.mark.asyncio
async def test_pipeline_generation_persists_analysis(session: AsyncSession) -> None:
    project_id, response = await make_completed_project(session)
    analysis = await get_analysis(session, project_id)
    assert response.analysis_id
    assert analysis.core_ideas


@pytest.mark.asyncio
async def test_xiaohongshu_persistence(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    contents = await list_project_contents(session, project_id, platform="xiaohongshu")
    assert len(contents) == 1
    assert len(contents[0].content["titles"]) == 10


@pytest.mark.asyncio
async def test_douyin_persistence(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    contents = await list_project_contents(session, project_id, platform="douyin")
    assert contents[0].content["script_30s"]


@pytest.mark.asyncio
async def test_wechat_persistence(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    contents = await list_project_contents(session, project_id, platform="wechat")
    assert contents[0].content["full_article"]


@pytest.mark.asyncio
async def test_score_persistence(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    contents = await list_project_contents(session, project_id)
    assert all(content.score.overall_score >= 70 for content in contents)
    assert all(content.score.dimensions for content in contents)
    assert all(content.score.score_version == "v2" for content in contents)
    assert all(content.score.ai_risk_level in {"low", "medium", "high"} for content in contents)


@pytest.mark.asyncio
async def test_score_full_persistence_reload(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    contents = await list_project_contents(session, project_id)
    selected = next(item for item in contents if item.platform == "douyin")
    reloaded = await list_project_contents(session, project_id, platform="douyin")
    assert reloaded[0].score.dimensions == selected.score.dimensions
    assert reloaded[0].score.risk_flags == selected.score.risk_flags
    assert reloaded[0].score.ai_risk_level == selected.score.ai_risk_level
    assert reloaded[0].score.risk_reasons == selected.score.risk_reasons
    assert reloaded[0].score.rewrite_suggestions == selected.score.rewrite_suggestions
    assert reloaded[0].score.score_version == "v2"


@pytest.mark.asyncio
async def test_content_update_creates_version(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    content = (await list_project_contents(session, project_id))[0]
    payload = dict(content.content)
    payload["cta"] = "新的 CTA"
    updated = await create_content_version(
        session, content.id, GeneratedContentUpdate(content=payload)
    )
    assert updated.version == 2
    assert updated.source == "manual_edit"


@pytest.mark.asyncio
async def test_version_history(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    content = (await list_project_contents(session, project_id))[0]
    await create_content_version(
        session,
        content.id,
        GeneratedContentUpdate(content=dict(content.content)),
    )
    versions = await list_versions(session, content.id)
    assert [item.version for item in versions] == [1, 2]


@pytest.mark.asyncio
async def test_get_specific_version(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    content = (await list_project_contents(session, project_id))[0]
    await create_content_version(
        session,
        content.id,
        GeneratedContentUpdate(content=dict(content.content)),
    )
    version = await get_version(session, content.id, 1)
    assert version.version == 1


@pytest.mark.asyncio
async def test_rewrite_creates_version(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    content = (await list_project_contents(session, project_id))[0]
    rewritten = await create_content_version(
        session,
        content.id,
        RewriteRequest(instruction="减少 AI 感", target="both"),
        rewrite=True,
    )
    assert rewritten.version == 2
    assert rewritten.source == "ai_rewrite"
    assert rewritten.score.dimensions
    assert rewritten.score.ai_risk_level in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_rewrite_version_score_persistence(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    content = (await list_project_contents(session, project_id))[0]
    rewritten = await create_content_version(
        session,
        content.id,
        RewriteRequest(
            instruction="reduce AI tone",
            target="both",
            instruction_type="reduce_ai_tone",
        ),
        rewrite=True,
    )
    version = await get_version(session, content.id, rewritten.version)
    assert version.score.score_version == "v2"
    assert version.score.dimensions == rewritten.score.dimensions
    assert version.score.ai_risk_level == rewritten.score.ai_risk_level


@pytest.mark.asyncio
async def test_markdown_export(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    markdown = await export_project_markdown(session, project_id)
    assert "# Lifecycle Test" in markdown
    assert "## xiaohongshu" in markdown


@pytest.mark.asyncio
async def test_dashboard_stats(session: AsyncSession) -> None:
    await make_completed_project(session)
    stats = await dashboard_stats(session)
    assert stats.total_projects == 1
    assert stats.generated_contents == 3


@pytest.mark.asyncio
async def test_repository_business_queries(session: AsyncSession) -> None:
    project_id, _ = await make_completed_project(session)
    repo = GeneratedContentRepository(session)
    all_versions = await repo.list_by_project(project_id, latest_only=False)
    assert len(all_versions) == 3
    assert await ProjectRepository(session).get_detail(project_id)


@pytest.mark.asyncio
async def test_failed_project_status(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await create_project(session, ProjectCreate(name="Will Fail"))

    async def fail_pipeline(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.projects.run_text_pipeline", fail_pipeline)
    with pytest.raises(HTTPException):
        await generate_project(
            session,
            project.id,
            ProjectGenerateRequest(title="Will Fail", raw_text=RAW_TEXT),
        )
    failed = await ProjectRepository(session).get_by_id(project.id)
    assert failed.status == "failed"
    assert failed.retryable is True
    assert await table_count(session, SourceContent) == 1
    assert await table_count(session, ContentAnalysis) == 0
    assert await table_count(session, GeneratedContent) == 0
    assert await table_count(session, ContentScore) == 0


@pytest.mark.asyncio
async def test_retry_failed_project(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    project = await create_project(session, ProjectCreate(name="Retry Flow"))
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
            session,
            project.id,
            ProjectGenerateRequest(title="Retry Flow", raw_text=RAW_TEXT),
        )
    assert await table_count(session, SourceContent) == 1
    assert await table_count(session, ContentAnalysis) == 0
    response = await retry_project(session, project.id)
    assert response.generated_contents
    assert await table_count(session, SourceContent) == 1
    assert await table_count(session, ContentAnalysis) == 1
    assert await table_count(session, GeneratedContent) == 3
    assert await table_count(session, ContentScore) == 3
    completed = await ProjectRepository(session).get_by_id(project.id)
    assert completed.status == "completed"
    assert completed.retryable is False


@pytest.mark.asyncio
async def test_second_retry_after_success_is_rejected(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await create_project(session, ProjectCreate(name="Retry Rejected"))
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
            session,
            project.id,
            ProjectGenerateRequest(title="Retry Rejected", raw_text=RAW_TEXT),
        )
    await retry_project(session, project.id)
    with pytest.raises(HTTPException):
        await retry_project(session, project.id)


@pytest.mark.asyncio
async def test_content_style_and_audience_persistence(session: AsyncSession) -> None:
    project = await create_project(
        session,
        ProjectCreate(
            name="Audience Project",
            content_style="professional_analysis",
            target_audience="AI beginners",
            audience_pain_points=["不知道如何开始"],
            audience_knowledge_level="beginner",
            content_goal="education",
        ),
    )
    detail = await get_project_detail(session, project.id)
    assert detail.content_style == "professional_analysis"
    assert detail.target_audience == "AI beginners"
    assert detail.audience_pain_points == ["不知道如何开始"]
