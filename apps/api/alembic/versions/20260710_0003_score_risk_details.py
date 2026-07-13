"""score risk details

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260710_0003"
down_revision: str | None = "20260710_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.TypeEngine:
    return postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.add_column("content_scores", sa.Column("risk_details", json_type(), nullable=True))
    if dialect == "postgresql":
        op.execute(
            """
            UPDATE content_scores
            SET risk_details =
              '{"ai_risk_level":"medium","risk_reasons":[],"rewrite_suggestions":[]}'::jsonb
            """
        )
    else:
        op.execute(
            """
            UPDATE content_scores
            SET risk_details =
              '{"ai_risk_level":"medium","risk_reasons":[],"rewrite_suggestions":[]}'
            """
        )
    if dialect != "sqlite":
        op.alter_column("content_scores", "risk_details", nullable=False)


def downgrade() -> None:
    op.drop_column("content_scores", "risk_details")
