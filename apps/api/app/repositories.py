from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ContentAnalysis, ContentScore, GeneratedContent, Project, SourceContent, User


class BaseRepository:
    model: type

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values):
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, item_id: str):
        return await self.session.get(self.model, item_id)

    async def list(self):
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def update(self, item_id: str, **values):
        instance = await self.get_by_id(item_id)
        if not instance:
            return None
        for key, value in values.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, item_id: str) -> bool:
        result = await self.session.execute(delete(self.model).where(self.model.id == item_id))
        return bool(result.rowcount)


class UserRepository(BaseRepository):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_or_create_demo_user(self) -> User:
        user = await self.get_by_email("demo@contentflow.cn")
        if user:
            return user
        return await self.create(email="demo@contentflow.cn", display_name="Demo Creator")


class ProjectRepository(BaseRepository):
    model = Project

    async def list_by_user(self, user_id: str) -> list[Project]:
        result = await self.session.execute(
            select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_detail(self, project_id: str) -> Project | None:
        result = await self.session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.source_contents)
                .selectinload(SourceContent.analysis)
                .selectinload(ContentAnalysis.generated_contents)
                .selectinload(GeneratedContent.score)
            )
        )
        return result.scalar_one_or_none()

    async def current_month_count(self, user_id: str) -> int:
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1)
        result = await self.session.execute(
            select(func.count(Project.id)).where(
                Project.user_id == user_id, Project.created_at >= month_start
            )
        )
        return int(result.scalar_one())


class SourceContentRepository(BaseRepository):
    model = SourceContent

    async def get_by_project(self, project_id: str) -> SourceContent | None:
        result = await self.session.execute(
            select(SourceContent)
            .where(SourceContent.project_id == project_id)
            .order_by(SourceContent.created_at.desc())
        )
        return result.scalars().first()


class AnalysisRepository(BaseRepository):
    model = ContentAnalysis

    async def get_by_project(self, project_id: str) -> ContentAnalysis | None:
        result = await self.session.execute(
            select(ContentAnalysis)
            .join(SourceContent)
            .where(SourceContent.project_id == project_id)
            .options(selectinload(ContentAnalysis.generated_contents).selectinload(GeneratedContent.score))
        )
        return result.scalars().first()


class GeneratedContentRepository(BaseRepository):
    model = GeneratedContent

    async def list_by_project(
        self,
        project_id: str,
        platform: str | None = None,
        content_type: str | None = None,
        version: int | None = None,
        latest_only: bool = True,
    ) -> list[GeneratedContent]:
        stmt = (
            select(GeneratedContent)
            .join(ContentAnalysis)
            .join(SourceContent)
            .where(SourceContent.project_id == project_id)
            .options(selectinload(GeneratedContent.score))
            .order_by(GeneratedContent.platform, GeneratedContent.version.desc())
        )
        if platform:
            stmt = stmt.where(GeneratedContent.platform == platform)
        if content_type:
            stmt = stmt.where(GeneratedContent.content_type == content_type)
        if version:
            stmt = stmt.where(GeneratedContent.version == version)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        if not latest_only:
            return rows
        latest: dict[str, GeneratedContent] = {}
        for row in rows:
            key = row.content_group_id or row.id
            if key not in latest:
                latest[key] = row
        return list(latest.values())

    async def get_with_score(self, content_id: str) -> GeneratedContent | None:
        result = await self.session.execute(
            select(GeneratedContent)
            .where(GeneratedContent.id == content_id)
            .options(
                selectinload(GeneratedContent.score),
                selectinload(GeneratedContent.analysis)
                .selectinload(ContentAnalysis.source_content)
                .selectinload(SourceContent.project),
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version(self, content_group_id: str) -> GeneratedContent | None:
        result = await self.session.execute(
            select(GeneratedContent)
            .where(GeneratedContent.content_group_id == content_group_id)
            .options(
                selectinload(GeneratedContent.score),
                selectinload(GeneratedContent.analysis)
                .selectinload(ContentAnalysis.source_content)
                .selectinload(SourceContent.project),
            )
            .order_by(GeneratedContent.version.desc())
        )
        return result.scalars().first()

    async def list_versions(self, content_group_id: str) -> list[GeneratedContent]:
        result = await self.session.execute(
            select(GeneratedContent)
            .where(GeneratedContent.content_group_id == content_group_id)
            .options(selectinload(GeneratedContent.score))
            .order_by(GeneratedContent.version)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count(GeneratedContent.id))
            .join(ContentAnalysis)
            .join(SourceContent)
            .join(Project)
            .where(Project.user_id == user_id)
        )
        return int(result.scalar_one())


class ScoreRepository(BaseRepository):
    model = ContentScore
