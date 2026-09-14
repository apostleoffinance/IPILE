"""allocation rules, runs, lines

Revision ID: 0005_allocation
Revises: 0004_obligations
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_allocation"
down_revision: Union[str, None] = "0004_obligations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "allocation_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("basis", sa.String(length=32), nullable=False, server_default="recognized_income"),
        sa.Column("rate", sa.Numeric(9, 6), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("destination_type", sa.String(length=20), nullable=False),
        sa.Column("destination_id", sa.Uuid(), nullable=True),
        sa.Column("income_source_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["income_source_id"], ["income_sources.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_allocation_rules_household_id", "allocation_rules", ["household_id"])

    op.create_table(
        "allocation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("recognized_income", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_allocated", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("surplus", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="computed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", "period_start", "period_end", name="uq_allocation_runs_period"),
    )
    op.create_index("ix_allocation_runs_household_id", "allocation_runs", ["household_id"])

    op.create_table(
        "allocation_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("requested_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("destination_type", sa.String(length=20), nullable=False),
        sa.Column("destination_id", sa.Uuid(), nullable=True),
        sa.Column("mandatory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("funded", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["allocation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["allocation_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_allocation_lines_household_id", "allocation_lines", ["household_id"])
    op.create_index("ix_allocation_lines_run_id", "allocation_lines", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_allocation_lines_run_id", table_name="allocation_lines")
    op.drop_index("ix_allocation_lines_household_id", table_name="allocation_lines")
    op.drop_table("allocation_lines")
    op.drop_index("ix_allocation_runs_household_id", table_name="allocation_runs")
    op.drop_table("allocation_runs")
    op.drop_index("ix_allocation_rules_household_id", table_name="allocation_rules")
    op.drop_table("allocation_rules")
