"""Prevent one income transaction from verifying multiple contribution receipts.

Revision ID: 0020_unique_contribution_transaction
Revises: 0019_member_permissions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_unique_contribution_transaction"
down_revision: Union[str, None] = "0019_member_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT transaction_id, COUNT(*) AS record_count
            FROM contribution_records
            WHERE transaction_id IS NOT NULL
            GROUP BY transaction_id
            HAVING COUNT(*) > 1
            """
        )
    ).mappings().all()
    if duplicates:
        ids = ", ".join(str(row["transaction_id"]) for row in duplicates[:10])
        raise RuntimeError(
            "Cannot enforce unique contribution transaction links; duplicate "
            f"transaction_id values exist: {ids}. Resolve duplicates before retrying."
        )
    op.create_index(
        "uq_contribution_records_transaction_id",
        "contribution_records",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("transaction_id IS NOT NULL"),
        sqlite_where=sa.text("transaction_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_contribution_records_transaction_id",
        table_name="contribution_records",
    )
