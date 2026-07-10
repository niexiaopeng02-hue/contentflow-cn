from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

JSONColumn = JSONB().with_variant(JSON(), "sqlite")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))

    projects: Mapped[list["Project"]] = relationship(back_populates="user")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="general")
    source_type: Mapped[str] = mapped_column(String(80), default="article")
    content_style: Mapped[str] = mapped_column(String(80), default="knowledge_practical")
    target_audience: Mapped[str | None] = mapped_column(Text)
    audience_pain_points: Mapped[list[str]] = mapped_column(JSONColumn, default=list)
    audience_knowledge_level: Mapped[str] = mapped_column(String(80), default="beginner")
    content_goal: Mapped[str] = mapped_column(String(80), default="education")
    target_platforms: Mapped[list[str]] = mapped_column(JSONColumn, default=list)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    failure_stage: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship(back_populates="projects")
    source_contents: Mapped[list["SourceContent"]] = relationship(back_populates="project")


class SourceContent(TimestampMixin, Base):
    __tablename__ = "source_contents"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    raw_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="source_contents")
    analysis: Mapped["ContentAnalysis"] = relationship(back_populates="source_content")


class ContentAnalysis(TimestampMixin, Base):
    __tablename__ = "content_analysis"

    source_content_id: Mapped[str] = mapped_column(
        ForeignKey("source_contents.id", ondelete="CASCADE"), unique=True, index=True
    )
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    analysis_json: Mapped[dict] = mapped_column(JSONColumn)

    source_content: Mapped[SourceContent] = relationship(back_populates="analysis")
    generated_contents: Mapped[list["GeneratedContent"]] = relationship(back_populates="analysis")


class GeneratedContent(TimestampMixin, Base):
    __tablename__ = "generated_contents"

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("content_analysis.id", ondelete="CASCADE"), index=True
    )
    content_group_id: Mapped[str | None] = mapped_column(String(80), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    content_type: Mapped[str] = mapped_column(String(60), default="platform_output", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(40), default="generated")
    content_json: Mapped[dict] = mapped_column(JSONColumn)
    markdown_export: Mapped[str] = mapped_column(Text)

    analysis: Mapped[ContentAnalysis] = relationship(back_populates="generated_contents")
    score: Mapped["ContentScore"] = relationship(back_populates="generated_content")


class ContentScore(TimestampMixin, Base):
    __tablename__ = "content_scores"

    generated_content_id: Mapped[str] = mapped_column(
        ForeignKey("generated_contents.id", ondelete="CASCADE"), unique=True, index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer)
    hook_score: Mapped[int] = mapped_column(Integer)
    readability_score: Mapped[int] = mapped_column(Integer)
    value_score: Mapped[int] = mapped_column(Integer)
    structure_score: Mapped[int] = mapped_column(Integer)
    ai_risk_score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[list[str]] = mapped_column(JSONColumn)
    dimensions: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    risk_flags: Mapped[list[str]] = mapped_column(JSONColumn, default=list)
    risk_details: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    score_version: Mapped[str] = mapped_column(String(20), default="v2")

    generated_content: Mapped[GeneratedContent] = relationship(back_populates="score")
