from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentAnalysis, ContentScore, GeneratedContent, Project
from app.repositories import (
    AnalysisRepository,
    GeneratedContentRepository,
    ProjectRepository,
    ScoreRepository,
    SourceContentRepository,
    UserRepository,
)
from app.schemas import (
    ContentAnalysisSchema,
    ContentScoreSchema,
    DashboardStats,
    GeneratedContentRead,
    GeneratedContentUpdate,
    PipelineResponse,
    PlatformStrategy,
    ProjectContext,
    ProjectCreate,
    ProjectDetail,
    ProjectGenerateRequest,
    ProjectRead,
    RewriteRequest,
    VersionRead,
)
from app.services.pipeline import evaluate_content, run_text_pipeline, to_markdown
from app.services.providers import PipelineError, ProviderError, get_provider


def score_to_schema(score) -> ContentScoreSchema:
    risk_details = getattr(score, "risk_details", {}) or {}
    return ContentScoreSchema(
        overall_score=score.overall_score,
        hook_score=score.hook_score,
        readability_score=score.readability_score,
        value_score=score.value_score,
        structure_score=score.structure_score,
        ai_risk_score=score.ai_risk_score,
        feedback=score.feedback,
        dimensions=getattr(score, "dimensions", {}) or {},
        risk_flags=getattr(score, "risk_flags", []) or [],
        score_version=getattr(score, "score_version", "v2") or "v2",
        ai_risk_level=risk_details.get("ai_risk_level", "medium"),
        risk_reasons=risk_details.get("risk_reasons", []),
        rewrite_suggestions=risk_details.get("rewrite_suggestions", []),
    )


async def persist_score(
    session: AsyncSession, generated_content_id: str, score: ContentScoreSchema
):
    return await ScoreRepository(session).create(
        generated_content_id=generated_content_id,
        overall_score=score.overall_score,
        hook_score=score.hook_score,
        readability_score=score.readability_score,
        value_score=score.value_score,
        structure_score=score.structure_score,
        ai_risk_score=score.ai_risk_score,
        feedback=score.feedback,
        dimensions=score.dimensions,
        risk_flags=score.risk_flags,
        risk_details={
            "ai_risk_level": score.ai_risk_level,
            "risk_reasons": score.risk_reasons,
            "rewrite_suggestions": score.rewrite_suggestions,
        },
        score_version=score.score_version,
    )


def generated_to_schema(content: GeneratedContent) -> GeneratedContentRead:
    return GeneratedContentRead(
        id=content.id,
        content_group_id=content.content_group_id or content.id,
        platform=content.platform,
        content_type=content.content_type,
        version=content.version,
        source=content.source,
        content=content.content_json,
        markdown_export=content.markdown_export,
        score=score_to_schema(content.score),
        created_at=content.created_at,
    )


async def project_to_read(session: AsyncSession, project: Project) -> ProjectRead:
    generated = await GeneratedContentRepository(session).list_by_project(
        project.id, latest_only=True
    )
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        source_type=project.source_type,
        content_style=project.content_style,
        target_audience=project.target_audience,
        audience_pain_points=project.audience_pain_points,
        audience_knowledge_level=project.audience_knowledge_level,
        content_goal=project.content_goal,
        target_platforms=project.target_platforms,
        status=project.status,
        failure_stage=project.failure_stage,
        error_message=project.error_message,
        retryable=project.retryable,
        created_at=project.created_at,
        generated_content_count=len(generated),
    )


async def get_demo_user(session: AsyncSession):
    return await UserRepository(session).get_or_create_demo_user()


async def create_project(session: AsyncSession, payload: ProjectCreate) -> ProjectRead:
    user = await get_demo_user(session)
    project = await ProjectRepository(session).create(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        source_type=payload.source_type,
        content_style=payload.content_style,
        target_audience=payload.target_audience,
        audience_pain_points=payload.audience_pain_points,
        audience_knowledge_level=payload.audience_knowledge_level,
        content_goal=payload.content_goal,
        target_platforms=payload.target_platforms,
        status="draft",
        retryable=False,
    )
    await session.commit()
    return await project_to_read(session, project)


async def list_projects(session: AsyncSession) -> list[ProjectRead]:
    user = await get_demo_user(session)
    projects = await ProjectRepository(session).list_by_user(user.id)
    return [await project_to_read(session, item) for item in projects]


async def dashboard_stats(session: AsyncSession) -> DashboardStats:
    user = await get_demo_user(session)
    project_repo = ProjectRepository(session)
    projects = await project_repo.list_by_user(user.id)
    reads = [await project_to_read(session, project) for project in projects]
    generated_count = await GeneratedContentRepository(session).count_by_user(user.id)
    month_count = await project_repo.current_month_count(user.id)
    return DashboardStats(
        total_projects=len(projects),
        generated_contents=generated_count,
        current_month_projects=month_count,
        latest_project=reads[0] if reads else None,
        recent_projects=reads[:8],
    )


async def get_project_detail(session: AsyncSession, project_id: str) -> ProjectDetail:
    project = await ProjectRepository(session).get_detail(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    base = await project_to_read(session, project)
    source = project.source_contents[-1] if project.source_contents else None
    analysis_model = source.analysis if source and source.analysis else None
    generated = await GeneratedContentRepository(session).list_by_project(
        project_id, latest_only=True
    )
    return ProjectDetail(
        **base.model_dump(),
        source_content=(
            {
                "id": source.id,
                "title": source.title,
                "raw_text": source.raw_text,
                "cleaned_text": source.cleaned_text,
                "created_at": source.created_at,
            }
            if source
            else None
        ),
        analysis=ContentAnalysisSchema.model_validate(analysis_model.analysis_json)
        if analysis_model
        else None,
        generated_contents=[generated_to_schema(item) for item in generated],
    )


async def delete_project(session: AsyncSession, project_id: str) -> None:
    deleted = await ProjectRepository(session).delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.commit()


async def generate_project(
    session: AsyncSession, project_id: str, payload: ProjectGenerateRequest
) -> PipelineResponse:
    project_repo = ProjectRepository(session)
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "processing"
    project.error_message = None
    project.failure_stage = None
    project.retryable = False
    project.target_platforms = payload.target_platforms
    source = await SourceContentRepository(session).create(
        project_id=project_id,
        title=payload.title,
        raw_text=payload.raw_text,
        cleaned_text=payload.raw_text.strip(),
    )
    await session.commit()
    try:
        return await _complete_generation_for_source(
            session,
            project_id,
            source.id,
            payload.target_platforms,
        )
    except (ProviderError, PipelineError) as exc:
        await _mark_project_failed(session, project_id, exc)
        raise HTTPException(status_code=500, detail="Pipeline failed safely") from exc
    except Exception as exc:
        await _mark_project_failed(session, project_id, exc)
        raise HTTPException(status_code=500, detail="Pipeline failed safely") from exc


async def retry_project(session: AsyncSession, project_id: str) -> PipelineResponse:
    project = await ProjectRepository(session).get_detail(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "failed" or not project.retryable:
        raise HTTPException(status_code=400, detail="Only retryable failed projects can be retried")
    source = project.source_contents[-1] if project.source_contents else None
    if not source:
        raise HTTPException(status_code=400, detail="Project has no source content to retry")
    project.status = "processing"
    project.error_message = None
    project.failure_stage = None
    project.retryable = False
    await _clear_generation_artifacts(session, source.id)
    await session.commit()
    try:
        return await _complete_generation_for_source(
            session,
            project_id,
            source.id,
            project.target_platforms,
        )
    except (ProviderError, PipelineError) as exc:
        await _mark_project_failed(session, project_id, exc)
        raise HTTPException(status_code=500, detail="Pipeline failed safely") from exc
    except Exception as exc:
        await _mark_project_failed(session, project_id, exc)
        raise HTTPException(status_code=500, detail="Pipeline failed safely") from exc


async def _complete_generation_for_source(
    session: AsyncSession,
    project_id: str,
    source_id: str,
    target_platforms: list[str],
) -> PipelineResponse:
    project = await ProjectRepository(session).get_by_id(project_id)
    source = await SourceContentRepository(session).get_by_id(source_id)
    if not project or not source:
        raise HTTPException(status_code=404, detail="Project source not found")
    context = ProjectContext(
        category=project.category,
        source_type=project.source_type,
        content_style=project.content_style,
        target_audience=project.target_audience,
        audience_pain_points=project.audience_pain_points,
        audience_knowledge_level=project.audience_knowledge_level,
        content_goal=project.content_goal,
    )
    cleaned_text, analysis_schema, generated = await run_text_pipeline(
        source.raw_text, target_platforms=target_platforms, context=context
    )
    source.cleaned_text = cleaned_text
    await _clear_generation_artifacts(session, source.id)
    analysis = await AnalysisRepository(session).create(
        source_content_id=source.id,
        analysis_json=analysis_schema.model_dump(),
    )
    for item in generated:
        generated_model = await GeneratedContentRepository(session).create(
            analysis_id=analysis.id,
            platform=item.platform,
            content_type=item.content_type,
            version=1,
            source="generated",
            content_json=item.content.model_dump()
            if hasattr(item.content, "model_dump")
            else dict(item.content),
            markdown_export=item.markdown_export,
        )
        generated_model.content_group_id = generated_model.id
        await session.flush()
        await persist_score(session, generated_model.id, item.score)
        item.id = generated_model.id
        item.content_group_id = generated_model.id
    project.status = "completed"
    project.error_message = None
    project.failure_stage = None
    project.retryable = False
    await session.commit()
    return PipelineResponse(
        source_content_id=source.id,
        analysis_id=analysis.id,
        analysis=analysis_schema,
        generated_contents=generated,
    )


async def _clear_generation_artifacts(session: AsyncSession, source_id: str) -> None:
    analysis_ids = select(ContentAnalysis.id).where(ContentAnalysis.source_content_id == source_id)
    content_ids = select(GeneratedContent.id).where(GeneratedContent.analysis_id.in_(analysis_ids))
    await session.execute(
        delete(ContentScore).where(ContentScore.generated_content_id.in_(content_ids))
    )
    await session.execute(
        delete(GeneratedContent).where(GeneratedContent.analysis_id.in_(analysis_ids))
    )
    await session.execute(
        delete(ContentAnalysis).where(ContentAnalysis.source_content_id == source_id)
    )
    await session.flush()


async def _mark_project_failed(
    session: AsyncSession, project_id: str, exc: Exception
) -> None:
    await session.rollback()
    project = await ProjectRepository(session).get_by_id(project_id)
    if project:
        project.status = "failed"
        project.failure_stage = getattr(exc, "stage", "pipeline")
        project.error_message = "Pipeline failed safely. Please retry."
        project.retryable = getattr(exc, "retryable", True)
        await session.commit()


async def get_analysis(session: AsyncSession, project_id: str) -> ContentAnalysisSchema:
    analysis = await AnalysisRepository(session).get_by_project(project_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return ContentAnalysisSchema.model_validate(analysis.analysis_json)


async def list_project_contents(
    session: AsyncSession,
    project_id: str,
    platform: str | None = None,
    content_type: str | None = None,
    version: int | None = None,
) -> list[GeneratedContentRead]:
    contents = await GeneratedContentRepository(session).list_by_project(
        project_id, platform=platform, content_type=content_type, version=version
    )
    return [generated_to_schema(item) for item in contents]


async def get_generated_content(session: AsyncSession, content_id: str) -> GeneratedContentRead:
    content = await GeneratedContentRepository(session).get_with_score(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Generated content not found")
    return generated_to_schema(content)


async def create_content_version(
    session: AsyncSession,
    content_id: str,
    payload: GeneratedContentUpdate | RewriteRequest,
    rewrite: bool = False,
) -> GeneratedContentRead:
    repo = GeneratedContentRepository(session)
    current = await repo.get_with_score(content_id)
    if not current:
        raise HTTPException(status_code=404, detail="Generated content not found")
    group_id = current.content_group_id or current.id
    latest = await repo.get_latest_version(group_id)
    if not latest:
        latest = current
    if rewrite:
        analysis = latest.analysis
        analysis_schema = ContentAnalysisSchema.model_validate(analysis.analysis_json)
        strategy = _strategy_for_platform(analysis_schema, latest.platform)
        project = analysis.source_content.project
        context = ProjectContext(
            category=project.category,
            source_type=project.source_type,
            content_style=project.content_style,
            target_audience=project.target_audience,
            audience_pain_points=project.audience_pain_points,
            audience_knowledge_level=project.audience_knowledge_level,
            content_goal=project.content_goal,
        )
        new_content = await get_provider().rewrite_content(
            current_content=latest.content_json,
            analysis=analysis_schema,
            strategy=strategy,
            previous_feedback=score_to_schema(latest.score),
            request=payload,
            context=context,
        )
    else:
        new_content = payload.content
        strategy = None
    score = evaluate_content(latest.platform, _content_proxy(new_content), strategy)
    new_model = await repo.create(
        analysis_id=latest.analysis_id,
        content_group_id=group_id,
        platform=latest.platform,
        content_type=latest.content_type,
        version=latest.version + 1,
        source="ai_rewrite" if rewrite else payload.source,
        content_json=new_content,
        markdown_export=to_markdown(latest.platform, _content_proxy(new_content)),
    )
    await persist_score(session, new_model.id, score)
    await session.commit()
    new_model = await repo.get_with_score(new_model.id)
    return generated_to_schema(new_model)


class _content_proxy(dict):
    def model_dump(self):
        return dict(self)

    def model_dump_json(self, ensure_ascii: bool = False):
        import json

        return json.dumps(self, ensure_ascii=ensure_ascii)


def _strategy_for_platform(analysis: ContentAnalysisSchema, platform: str) -> PlatformStrategy:
    raw = analysis.platform_strategy.get(platform)
    if isinstance(raw, str):
        import json

        raw = json.loads(raw)
    if isinstance(raw, dict):
        return PlatformStrategy.model_validate(raw)
    return PlatformStrategy(
        platform=platform,
        audience_intent="consume useful content",
        content_angle=analysis.content_angle,
        hook_strategy="make the main value clear",
        tone=analysis.tone,
        structure=["hook", "body", "cta"],
        length_target="platform appropriate",
        cta_strategy="ask a relevant question",
        information_density="medium",
        emotion_level="medium",
        commercial_tone="low",
        forbidden_behavior=["fake data", "fake personal experience"],
    )


async def list_versions(session: AsyncSession, content_id: str) -> list[VersionRead]:
    content = await GeneratedContentRepository(session).get_with_score(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Generated content not found")
    versions = await GeneratedContentRepository(session).list_versions(
        content.content_group_id or content.id
    )
    return [
        VersionRead(
            id=item.id,
            content_group_id=item.content_group_id or item.id,
            platform=item.platform,
            content_type=item.content_type,
            version=item.version,
            source=item.source,
            content=item.content_json,
            markdown_export=item.markdown_export,
            score=score_to_schema(item.score),
            created_at=item.created_at,
        )
        for item in versions
    ]


async def get_version(session: AsyncSession, content_id: str, version: int) -> VersionRead:
    versions = await list_versions(session, content_id)
    for item in versions:
        if item.version == version:
            return item
    raise HTTPException(status_code=404, detail="Version not found")


async def export_project_markdown(session: AsyncSession, project_id: str) -> str:
    detail = await get_project_detail(session, project_id)
    lines = [f"# {detail.name}", ""]
    if detail.analysis:
        lines.extend(["## Source Summary", detail.analysis.summary, ""])
        lines.append("## Core Ideas")
        lines.extend(f"- {idea}" for idea in detail.analysis.core_ideas)
        lines.append("")
    for content in detail.generated_contents:
        lines.extend([f"## {content.platform}", ""])
        for key, value in dict(content.content).items():
            lines.append(f"### {key.replace('_', ' ').title()}")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            else:
                lines.append(str(value))
            lines.append("")
    return "\n".join(lines).strip() + "\n"
