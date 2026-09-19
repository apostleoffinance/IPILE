"""Phase 15: giving policies/records + foundation completion columns

Revision ID: 0015_phase15
Revises: 0014_public_product
Create Date: 2026-09-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_phase15"
down_revision: Union[str, None] = "0014_public_product"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "giving_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("annual_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("requires_dual_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allocation_rule_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["allocation_rule_id"], ["allocation_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_giving_policies_household_id", "giving_policies", ["household_id"])

    op.create_table(
        "giving_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("beneficiary", sa.String(length=200), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="NGN"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("allocation_rule_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="posted"),
        sa.Column("created_by_member_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_member_id", sa.Uuid(), nullable=True),
        sa.Column("limit_warning", sa.Text(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["giving_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["allocation_rule_id"], ["allocation_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_member_id"], ["household_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_member_id"], ["household_members.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_giving_records_household_id", "giving_records", ["household_id"])
    op.create_index("ix_giving_records_policy_id", "giving_records", ["policy_id"])
    op.create_foreign_key(
        "fk_giving_records_transaction_id",
        "giving_records",
        "transactions",
        ["transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "transactions",
        sa.Column("giving_record_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_giving_record_id",
        "transactions",
        "giving_records",
        ["giving_record_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_giving_record_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "giving_record_id")
    op.drop_constraint("fk_giving_records_transaction_id", "giving_records", type_="foreignkey")
    op.drop_index("ix_giving_records_policy_id", table_name="giving_records")
    op.drop_index("ix_giving_records_household_id", table_name="giving_records")
    op.drop_table("giving_records")
    op.drop_index("ix_giving_policies_household_id", table_name="giving_policies")
    op.drop_table("giving_policies")
