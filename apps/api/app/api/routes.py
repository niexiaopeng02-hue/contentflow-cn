from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas import (
    ContentAnalysisSchema,
    DashboardStats,
    GeneratedContentRead,
    GeneratedContentUpdate,
    PipelineResponse,
    ProjectCreate,
    ProjectDetail,
    ProjectGenerateRequest,
    ProjectRead,
    RewriteRequest,
    SourceContentCreate,
    VersionRead,
)
from app.services.pipeline import run_preview_pipeline
from app.services.projects import (
    create_content_version,
    create_project,
    dashboard_stats,
    delete_project,
    export_project_markdown,
    generate_project,
    get_analysis,
    get_generated_content,
    get_project_detail,
    get_version,
    list_project_contents,
    list_projects,
    list_versions,
    retry_project,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(session: SessionDep) -> DashboardStats:
    return await dashboard_stats(session)


@router.post("/projects", response_model=ProjectRead)
async def post_project(payload: ProjectCreate, session: SessionDep) -> ProjectRead:
    return await create_project(session, payload)


@router.get("/projects", response_model=list[ProjectRead])
async def get_projects(session: SessionDep) -> list[ProjectRead]:
    return await list_projects(session)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str, session: SessionDep) -> ProjectDetail:
    return await get_project_detail(session, project_id)


@router.delete("/projects/{project_id}", status_code=204)
async def remove_project(project_id: str, session: SessionDep) -> Response:
    await delete_project(session, project_id)
    return Response(status_code=204)


@router.post("/projects/{project_id}/generate", response_model=PipelineResponse)
async def post_generate_project(
    project_id: str, payload: ProjectGenerateRequest, session: SessionDep
) -> PipelineResponse:
    return await generate_project(session, project_id, payload)


@router.post("/projects/{project_id}/retry", response_model=PipelineResponse)
async def post_retry_project(project_id: str, session: SessionDep) -> PipelineResponse:
    return await retry_project(session, project_id)


@router.get("/projects/{project_id}/analysis", response_model=ContentAnalysisSchema)
async def get_project_analysis(project_id: str, session: SessionDep) -> ContentAnalysisSchema:
    return await get_analysis(session, project_id)


@router.get("/projects/{project_id}/contents", response_model=list[GeneratedContentRead])
async def get_project_contents(
    project_id: str,
    session: SessionDep,
    platform: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    version: int | None = Query(default=None),
) -> list[GeneratedContentRead]:
    return await list_project_contents(session, project_id, platform, content_type, version)


@router.get("/generated-contents/{content_id}", response_model=GeneratedContentRead)
async def get_content(content_id: str, session: SessionDep) -> GeneratedContentRead:
    return await get_generated_content(session, content_id)


@router.patch("/generated-contents/{content_id}", response_model=GeneratedContentRead)
async def patch_content(
    content_id: str, payload: GeneratedContentUpdate, session: SessionDep
) -> GeneratedContentRead:
    return await create_content_version(session, content_id, payload)


@router.post("/generated-contents/{content_id}/rewrite", response_model=GeneratedContentRead)
async def post_rewrite(
    content_id: str, payload: RewriteRequest, session: SessionDep
) -> GeneratedContentRead:
    return await create_content_version(session, content_id, payload, rewrite=True)


@router.get("/generated-contents/{content_id}/versions", response_model=list[VersionRead])
async def get_content_versions(content_id: str, session: SessionDep) -> list[VersionRead]:
    return await list_versions(session, content_id)


@router.get("/generated-contents/{content_id}/versions/{version}", response_model=VersionRead)
async def get_content_version(content_id: str, version: int, session: SessionDep) -> VersionRead:
    return await get_version(session, content_id, version)


@router.get("/projects/{project_id}/export/markdown")
async def get_markdown_export(project_id: str, session: SessionDep) -> Response:
    markdown = await export_project_markdown(session, project_id)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{project_id}.md"'},
    )


@router.post("/pipeline/preview", response_model=PipelineResponse)
async def preview_pipeline(payload: SourceContentCreate) -> PipelineResponse:
    return await run_preview_pipeline(payload.raw_text)
