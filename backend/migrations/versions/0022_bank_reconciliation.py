"""Add reconciliation sessions and bank connections.

Revision ID: 0022_bank_reconciliation
Revises: 0021_receipt_intelligence
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
revision: str = "0022_bank_reconciliation"
down_revision: Union[str, None] = "0021_receipt_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("bank_connections",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False), sa.Column("created_by_member_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False), sa.Column("link_reference", sa.String(64), nullable=False),
        sa.Column("provider_account_id_encrypted", sa.Text()), sa.Column("provider_account_id_hash", sa.String(64)),
        sa.Column("institution_name", sa.String(200)), sa.Column("masked_account_number", sa.String(4)),
        sa.Column("currency", sa.String(3)), sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("data_status", sa.String(24), server_default="PROCESSING", nullable=False),
        sa.Column("provider_balance", sa.Numeric(18,2)), sa.Column("provider_balance_as_of", sa.DateTime(timezone=True)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_member_id"], ["household_members.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("link_reference", name="uq_bank_connections_link_reference"),
        sa.UniqueConstraint("household_id", "provider", "provider_account_id_hash", name="uq_bank_connection_household_provider_account"))
    for col in ("household_id", "account_id", "provider_account_id_hash"):
        op.create_index(f"ix_bank_connections_{col}", "bank_connections", [col])
    op.create_table("reconciliation_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False), sa.Column("created_by_member_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(24), nullable=False), sa.Column("status", sa.String(24), server_default="review", nullable=False),
        sa.Column("statement_start", sa.Date()), sa.Column("statement_end", sa.Date()),
        sa.Column("opening_balance", sa.Numeric(18,2)), sa.Column("closing_balance", sa.Numeric(18,2)),
        sa.Column("calculated_closing_balance", sa.Numeric(18,2)), sa.Column("balance_difference", sa.Numeric(18,2)),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("matched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("suggested_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unmatched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conflict_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("source IN ('statement','mono')", name="ck_reconciliation_sessions_source"),
        sa.CheckConstraint("status IN ('review','completed','cancelled')", name="ck_reconciliation_sessions_status"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_member_id"], ["household_members.id"], ondelete="RESTRICT"))
    for col in ("household_id", "account_id"):
        op.create_index(f"ix_reconciliation_sessions_{col}", "reconciliation_sessions", [col])
    op.create_table("reconciliation_items",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False), sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(24), nullable=False), sa.Column("source_reference", sa.String(200), nullable=False),
        sa.Column("date", sa.Date(), nullable=False), sa.Column("amount", sa.Numeric(18,2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False), sa.Column("type", sa.String(32), nullable=False),
        sa.Column("description", sa.String(500)), sa.Column("merchant", sa.String(200)),
        sa.Column("provider_category", sa.String(80)), sa.Column("provider_balance", sa.Numeric(18,2)),
        sa.Column("suggested_transaction_id", sa.Uuid()), sa.Column("matched_transaction_id", sa.Uuid()),
        sa.Column("match_score", sa.Numeric(5,4)), sa.Column("match_reason", sa.String(300)),
        sa.Column("status", sa.String(24), server_default="unmatched", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source IN ('statement','mono')", name="ck_reconciliation_items_source"),
        sa.CheckConstraint("amount >= 0", name="ck_reconciliation_items_amount_nonneg"),
        sa.CheckConstraint("status IN ('suggested','unmatched','conflict','matched','posted','ignored')", name="ck_reconciliation_items_status"),
        sa.CheckConstraint("match_score IS NULL OR (match_score >= 0 AND match_score <= 1)", name="ck_reconciliation_items_match_score"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["reconciliation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["suggested_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("household_id", "account_id", "source", "source_reference", name="uq_reconciliation_item_source_reference"),
        sa.UniqueConstraint("matched_transaction_id", name="uq_reconciliation_item_matched_transaction"))
    for col in ("household_id", "session_id", "account_id"):
        op.create_index(f"ix_reconciliation_items_{col}", "reconciliation_items", [col])
    op.create_table("bank_webhook_events",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("event_id", sa.String(160), nullable=False), sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "event_id", name="uq_bank_webhook_provider_event"))

def downgrade() -> None:
    op.drop_table("bank_webhook_events")
    for col in ("household_id", "session_id", "account_id"):
        op.drop_index(f"ix_reconciliation_items_{col}", table_name="reconciliation_items")
    op.drop_table("reconciliation_items")
    for col in ("household_id", "account_id"):
        op.drop_index(f"ix_reconciliation_sessions_{col}", table_name="reconciliation_sessions")
    op.drop_table("reconciliation_sessions")
    for col in ("household_id", "account_id", "provider_account_id_hash"):
        op.drop_index(f"ix_bank_connections_{col}", table_name="bank_connections")
    op.drop_table("bank_connections")
