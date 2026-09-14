"""obligations, occurrences, sinking funds

Revision ID: 0004_obligations
Revises: 0003_planning
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_obligations"
down_revision: Union[str, None] = "0003_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "obligations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="monthly"),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("sinking_fund", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_allocate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("beneficiary_name", sa.String(length=200), nullable=True),
        sa.Column("beneficiary_member_id", sa.Uuid(), nullable=True),
        sa.Column("fund_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["beneficiary_member_id"], ["household_members.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_obligations_household_id", "obligations", ["household_id"])

    op.create_table(
        "sinking_funds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("obligation_id", sa.Uuid(), nullable=True),
        sa.Column("monthly_contribution", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obligation_id"], ["obligations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sinking_funds_household_id", "sinking_funds", ["household_id"])
    op.create_foreign_key(
        "fk_obligations_fund_id",
        "obligations",
        "sinking_funds",
        ["fund_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "obligation_occurrences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("obligation_id", sa.Uuid(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("funded_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="upcoming"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obligation_id"], ["obligations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("obligation_id", "due_date", name="uq_obligation_occurrences_due"),
    )
    op.create_index("ix_obligation_occurrences_household_id", "obligation_occurrences", ["household_id"])
    op.create_index("ix_obligation_occurrences_obligation_id", "obligation_occurrences", ["obligation_id"])

    op.create_table(
        "fund_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("fund_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fund_id"], ["sinking_funds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_fund_contributions_household_id", "fund_contributions", ["household_id"])
    op.create_index("ix_fund_contributions_fund_id", "fund_contributions", ["fund_id"])

    op.add_column("transactions", sa.Column("obligation_id", sa.Uuid(), nullable=True))
    op.add_column("transactions", sa.Column("fund_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_obligation_id",
        "transactions",
        "obligations",
        ["obligation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transactions_fund_id",
        "transactions",
        "sinking_funds",
        ["fund_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_fund_id", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_obligation_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "fund_id")
    op.drop_column("transactions", "obligation_id")
    op.drop_table("fund_contributions")
    op.drop_table("obligation_occurrences")
    op.drop_constraint("fk_obligations_fund_id", "obligations", type_="foreignkey")
    op.drop_table("sinking_funds")
    op.drop_table("obligations")
