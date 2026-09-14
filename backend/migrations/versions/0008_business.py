"""businesses, employees, business transactions

Revision ID: 0008_business
Revises: 0007_goals
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_business"
down_revision: Union[str, None] = "0007_goals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("business_id", sa.Uuid(), nullable=True))
    op.add_column("transactions", sa.Column("business_id", sa.Uuid(), nullable=True))

    op.create_table(
        "businesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False, server_default="other"),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
            name="fk_businesses_account_id",
        ),
    )
    op.create_index("ix_businesses_household_id", "businesses", ["household_id"])

    op.create_foreign_key(
        "fk_accounts_business_id",
        "accounts",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transactions_business_id",
        "transactions",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "business_employees",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False, server_default="staff"),
        sa.Column("compensation", sa.Numeric(18, 2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_business_employees_household_id", "business_employees", ["household_id"])
    op.create_index("ix_business_employees_business_id", "business_employees", ["business_id"])

    op.create_table(
        "business_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("household_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["business_employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["household_transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
            name="fk_business_transactions_household_tx",
        ),
    )
    op.create_index("ix_business_transactions_household_id", "business_transactions", ["household_id"])
    op.create_index("ix_business_transactions_business_id", "business_transactions", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_business_transactions_business_id", table_name="business_transactions")
    op.drop_index("ix_business_transactions_household_id", table_name="business_transactions")
    op.drop_table("business_transactions")
    op.drop_index("ix_business_employees_business_id", table_name="business_employees")
    op.drop_index("ix_business_employees_household_id", table_name="business_employees")
    op.drop_table("business_employees")
    op.drop_constraint("fk_transactions_business_id", "transactions", type_="foreignkey")
    op.drop_constraint("fk_accounts_business_id", "accounts", type_="foreignkey")
    op.drop_index("ix_businesses_household_id", table_name="businesses")
    op.drop_table("businesses")
    op.drop_column("transactions", "business_id")
    op.drop_column("accounts", "business_id")
