"""Add household Gmail alert connections.

Revision ID: 0024_gmail_alert_connections
Revises: 0023_multi_currency
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_gmail_alert_connections"
down_revision: Union[str, None] = "0023_multi_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gmail_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "household_id",
            sa.Uuid(),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state_hash", sa.String(64), nullable=True),
        sa.Column("state_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_address", sa.String(320), nullable=True),
        sa.Column("google_subject", sa.String(200), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_internal_date", sa.BigInteger(), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("household_id", name="uq_gmail_connections_household"),
    )
    op.create_index("ix_gmail_connections_state_hash", "gmail_connections", ["state_hash"])


def downgrade() -> None:
    op.drop_index("ix_gmail_connections_state_hash", table_name="gmail_connections")
    op.drop_table("gmail_connections")
