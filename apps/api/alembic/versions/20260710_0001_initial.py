"""initial schema

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeEngine

from alembic import op

revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> TypeEngine:
    return postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("target_platforms", json_type(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_user_id"), "projects", ["user_id"])

    op.create_table(
        "source_contents",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_contents_project_id"), "source_contents", ["project_id"])

    op.create_table(
        "content_analysis",
        sa.Column("source_content_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("analysis_json", json_type(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_content_id"], ["source_contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_content_id"),
    )
    op.create_index(
        op.f("ix_content_analysis_source_content_id"),
        "content_analysis",
        ["source_content_id"],
        unique=True,
    )

    op.create_table(
        "generated_contents",
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("content_group_id", sa.String(length=80), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("content_type", sa.String(length=60), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("content_json", json_type(), nullable=False),
        sa.Column("markdown_export", sa.Text(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["content_analysis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_contents_analysis_id"), "generated_contents", ["analysis_id"]
    )
    op.create_index(
        op.f("ix_generated_contents_content_group_id"),
        "generated_contents",
        ["content_group_id"],
    )
    op.create_index(
        op.f("ix_generated_contents_content_type"), "generated_contents", ["content_type"]
    )
    op.create_index(op.f("ix_generated_contents_platform"), "generated_contents", ["platform"])

    op.create_table(
        "content_scores",
        sa.Column("generated_content_id", sa.String(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("hook_score", sa.Integer(), nullable=False),
        sa.Column("readability_score", sa.Integer(), nullable=False),
        sa.Column("value_score", sa.Integer(), nullable=False),
        sa.Column("structure_score", sa.Integer(), nullable=False),
        sa.Column("ai_risk_score", sa.Integer(), nullable=False),
        sa.Column("feedback", json_type(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["generated_content_id"], ["generated_contents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generated_content_id"),
    )
    op.create_index(
        op.f("ix_content_scores_generated_content_id"),
        "content_scores",
        ["generated_content_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("content_scores")
    op.drop_table("generated_contents")
    op.drop_table("content_analysis")
    op.drop_table("source_contents")
    op.drop_table("projects")
    op.drop_table("users")
