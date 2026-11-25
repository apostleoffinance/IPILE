import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class BankConnection(Base):
    __tablename__ = "bank_connections"
    __table_args__ = (
        UniqueConstraint("link_reference", name="uq_bank_connections_link_reference"),
        UniqueConstraint("household_id", "provider", "provider_account_id_hash", name="uq_bank_connection_household_provider_account"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), index=True)
    created_by_member_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("household_members.id", ondelete="RESTRICT"))
    provider: Mapped[str] = mapped_column(String(24), default="mono")
    link_reference: Mapped[str] = mapped_column(String(64))
    provider_account_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_account_id_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    institution_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    masked_account_number: Mapped[str | None] = mapped_column(String(4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")
    data_status: Mapped[str] = mapped_column(String(24), default="PROCESSING", server_default="PROCESSING")
    provider_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    provider_balance_as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ReconciliationSession(Base):
    __tablename__ = "reconciliation_sessions"
    __table_args__ = (CheckConstraint("source IN ('statement', 'mono')", name="ck_reconciliation_sessions_source"), CheckConstraint("status IN ('review', 'completed', 'cancelled')", name="ck_reconciliation_sessions_status"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), index=True)
    created_by_member_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("household_members.id", ondelete="RESTRICT"))
    source: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), default="review", server_default="review")
    statement_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    statement_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    calculated_closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance_difference: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_rows: Mapped[int] = mapped_column(default=0, server_default="0")
    duplicate_rows: Mapped[int] = mapped_column(default=0, server_default="0")
    matched_count: Mapped[int] = mapped_column(default=0, server_default="0")
    suggested_count: Mapped[int] = mapped_column(default=0, server_default="0")
    unmatched_count: Mapped[int] = mapped_column(default=0, server_default="0")
    conflict_count: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"
    __table_args__ = (
        UniqueConstraint("household_id", "account_id", "source", "source_reference", name="uq_reconciliation_item_source_reference"),
        UniqueConstraint("matched_transaction_id", name="uq_reconciliation_item_matched_transaction"),
        CheckConstraint("source IN ('statement', 'mono')", name="ck_reconciliation_items_source"),
        CheckConstraint("amount >= 0", name="ck_reconciliation_items_amount_nonneg"),
        CheckConstraint("status IN ('suggested', 'unmatched', 'conflict', 'matched', 'posted', 'ignored')", name="ck_reconciliation_items_status"),
        CheckConstraint("match_score IS NULL OR (match_score >= 0 AND match_score <= 1)", name="ck_reconciliation_items_match_score"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), index=True)
    source: Mapped[str] = mapped_column(String(24))
    source_reference: Mapped[str] = mapped_column(String(200))
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    type: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    suggested_transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    matched_transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    match_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="unmatched", server_default="unmatched")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BankWebhookEvent(Base):
    __tablename__ = "bank_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_bank_webhook_provider_event"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(24))
    event_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(120))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
