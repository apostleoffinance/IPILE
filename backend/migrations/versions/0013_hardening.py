"""audit logs for money, rules, members, exports, deletion

Revision ID: 0013_hardening
Revises: 0012_imports
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_hardening"
down_revision: Union[str, None] = "0012_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_household_id", "audit_logs", ["household_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_transactions_household_date",
        "transactions",
        ["household_id", "date"],
    )
    op.create_index(
        "ix_transactions_household_type",
        "transactions",
        ["household_id", "type"],
    )
    op.create_index(
        "ix_alerts_household_status",
        "alerts",
        ["household_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_household_status", table_name="alerts")
    op.drop_index("ix_transactions_household_type", table_name="transactions")
    op.drop_index("ix_transactions_household_date", table_name="transactions")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_household_id", table_name="audit_logs")
    op.drop_table("audit_logs")
