"""ai quality fields

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260710_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.TypeEngine:
    return postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.add_column("projects", sa.Column("content_style", sa.String(length=80), nullable=True))
    op.add_column("projects", sa.Column("target_audience", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("audience_pain_points", json_type(), nullable=True))
    op.add_column(
        "projects", sa.Column("audience_knowledge_level", sa.String(length=80), nullable=True)
    )
    op.add_column("projects", sa.Column("content_goal", sa.String(length=80), nullable=True))
    op.add_column("projects", sa.Column("failure_stage", sa.String(length=80), nullable=True))
    op.add_column("projects", sa.Column("retryable", sa.Boolean(), nullable=True))
    op.execute("UPDATE projects SET content_style = 'knowledge_practical'")
    op.execute("UPDATE projects SET audience_pain_points = '[]'")
    op.execute("UPDATE projects SET audience_knowledge_level = 'beginner'")
    op.execute("UPDATE projects SET content_goal = 'education'")
    op.execute("UPDATE projects SET retryable = 0")
    if dialect != "sqlite":
        op.alter_column("projects", "content_style", nullable=False)
        op.alter_column("projects", "audience_pain_points", nullable=False)
        op.alter_column("projects", "audience_knowledge_level", nullable=False)
        op.alter_column("projects", "content_goal", nullable=False)
        op.alter_column("projects", "retryable", nullable=False)

    op.add_column("content_scores", sa.Column("dimensions", json_type(), nullable=True))
    op.add_column("content_scores", sa.Column("risk_flags", json_type(), nullable=True))
    op.add_column("content_scores", sa.Column("score_version", sa.String(length=20), nullable=True))
    op.execute("UPDATE content_scores SET dimensions = '{}'")
    op.execute("UPDATE content_scores SET risk_flags = '[]'")
    op.execute("UPDATE content_scores SET score_version = 'v2'")
    if dialect != "sqlite":
        op.alter_column("content_scores", "dimensions", nullable=False)
        op.alter_column("content_scores", "risk_flags", nullable=False)
        op.alter_column("content_scores", "score_version", nullable=False)


def downgrade() -> None:
    op.drop_column("content_scores", "score_version")
    op.drop_column("content_scores", "risk_flags")
    op.drop_column("content_scores", "dimensions")
    op.drop_column("projects", "retryable")
    op.drop_column("projects", "failure_stage")
    op.drop_column("projects", "content_goal")
    op.drop_column("projects", "audience_knowledge_level")
    op.drop_column("projects", "audience_pain_points")
    op.drop_column("projects", "target_audience")
    op.drop_column("projects", "content_style")
