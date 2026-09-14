"""goals and goal contributions

Revision ID: 0007_goals
Revises: 0006_wealth
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_goals"
down_revision: Union[str, None] = "0006_wealth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("monthly_contribution", sa.Numeric(18, 2), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("funding_source_account_id", sa.Uuid(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["funding_source_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_goals_household_id", "goals", ["household_id"])

    op.add_column(
        "transactions",
        sa.Column("goal_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_goal_id",
        "transactions",
        "goals",
        ["goal_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
            name="fk_goal_contributions_transaction_id",
        ),
    )
    op.create_index("ix_goal_contributions_household_id", "goal_contributions", ["household_id"])
    op.create_index("ix_goal_contributions_goal_id", "goal_contributions", ["goal_id"])


def downgrade() -> None:
    op.drop_index("ix_goal_contributions_goal_id", table_name="goal_contributions")
    op.drop_index("ix_goal_contributions_household_id", table_name="goal_contributions")
    op.drop_table("goal_contributions")
    op.drop_constraint("fk_transactions_goal_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "goal_id")
    op.drop_index("ix_goals_household_id", table_name="goals")
    op.drop_table("goals")
