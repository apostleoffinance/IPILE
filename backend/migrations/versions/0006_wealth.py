"""assets, liabilities, investments, net worth snapshots

Revision ID: 0006_wealth
Revises: 0005_allocation
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_wealth"
down_revision: Union[str, None] = "0005_allocation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("include_in_net_worth", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_assets_household_id", "assets", ["household_id"])

    op.create_table(
        "liabilities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("interest_rate", sa.Numeric(9, 6), nullable=True),
        sa.Column("minimum_payment", sa.Numeric(18, 2), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("include_in_net_worth", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_liabilities_household_id", "liabilities", ["household_id"])

    op.create_table(
        "investments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="other"),
        sa.Column("current_value", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("cost_basis", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("institution", sa.String(length=200), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("include_in_net_worth", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_investments_household_id", "investments", ["household_id"])

    op.create_table(
        "investment_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("investment_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investment_id"], ["investments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_investment_transactions_household_id", "investment_transactions", ["household_id"])
    op.create_index("ix_investment_transactions_investment_id", "investment_transactions", ["investment_id"])

    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("total_assets", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_liabilities", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("net_worth", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("emergency_fund", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("investments", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("debt", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("breakdown", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", "period_start", name="uq_net_worth_snapshots_period"),
    )
    op.create_index("ix_net_worth_snapshots_household_id", "net_worth_snapshots", ["household_id"])


def downgrade() -> None:
    op.drop_index("ix_net_worth_snapshots_household_id", table_name="net_worth_snapshots")
    op.drop_table("net_worth_snapshots")
    op.drop_index("ix_investment_transactions_investment_id", table_name="investment_transactions")
    op.drop_index("ix_investment_transactions_household_id", table_name="investment_transactions")
    op.drop_table("investment_transactions")
    op.drop_index("ix_investments_household_id", table_name="investments")
    op.drop_table("investments")
    op.drop_index("ix_liabilities_household_id", table_name="liabilities")
    op.drop_table("liabilities")
    op.drop_index("ix_assets_household_id", table_name="assets")
    op.drop_table("assets")
    op.drop_column("accounts", "is_emergency")
