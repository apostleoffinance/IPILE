"""financial snapshots, scores, and reports

Revision ID: 0009_analytics
Revises: 0008_business
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_analytics"
down_revision: Union[str, None] = "0008_business"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "financial_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("income", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("expenses", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("savings", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("investments", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("giving", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("debt_reduction", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("surplus", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("net_worth", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("health_score", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", "period_start", name="uq_financial_snapshots_period"),
    )
    op.create_index("ix_financial_snapshots_household_id", "financial_snapshots", ["household_id"])

    op.create_table(
        "financial_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("score", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("label", sa.String(length=20), nullable=False, server_default="Critical"),
        sa.Column("components", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", "period_start", name="uq_financial_scores_period"),
    )
    op.create_index("ix_financial_scores_household_id", "financial_scores", ["household_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", "kind", "period_start", name="uq_reports_kind_period"),
    )
    op.create_index("ix_reports_household_id", "reports", ["household_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_household_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_financial_scores_household_id", table_name="financial_scores")
    op.drop_table("financial_scores")
    op.drop_index("ix_financial_snapshots_household_id", table_name="financial_snapshots")
    op.drop_table("financial_snapshots")
