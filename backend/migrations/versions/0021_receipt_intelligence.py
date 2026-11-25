"""Add receipt OCR review records.

Revision ID: 0021_receipt_intelligence
Revises: 0020_unique_contrib_txn
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_receipt_intelligence"
down_revision: Union[str, None] = "0020_unique_contrib_txn"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "receipt_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=200), nullable=True),
        sa.Column("media_type", sa.String(length=40), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending_review"),
        sa.Column("extracted", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("merchant", sa.String(length=200), nullable=True),
        sa.Column("receipt_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", name="uq_receipt_documents_transaction_id"),
        sa.UniqueConstraint("household_id", "content_sha256", name="uq_receipt_household_content"),
    )
    op.create_index("ix_receipt_documents_household_id", "receipt_documents", ["household_id"])
    op.create_index("ix_receipt_documents_account_id", "receipt_documents", ["account_id"])
    op.create_index("ix_receipt_documents_status", "receipt_documents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_receipt_documents_status", table_name="receipt_documents")
    op.drop_index("ix_receipt_documents_account_id", table_name="receipt_documents")
    op.drop_index("ix_receipt_documents_household_id", table_name="receipt_documents")
    op.drop_table("receipt_documents")
