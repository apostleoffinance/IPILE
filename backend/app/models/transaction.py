import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transactions_amount_nonneg"),
        CheckConstraint(
            "access_scope IN ('shared', 'personal')",
            name="ck_transactions_access_scope",
        ),
        CheckConstraint(
            "(access_scope = 'shared') OR (access_scope = 'personal' AND member_id IS NOT NULL)",
            name="ck_transactions_personal_owner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    counterparty_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("household_members.id", ondelete="SET NULL"), nullable=True
    )
    access_scope: Mapped[str] = mapped_column(String(20), default="shared", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exchange_rate_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    counterparty_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    counterparty_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    counterparty_base_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    counterparty_exchange_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 12), nullable=True
    )
    counterparty_exchange_rate_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    counterparty_exchange_rate_source: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )
    type: Mapped[str] = mapped_column(String(32))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date)
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    income_source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True
    )
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "obligations.id", ondelete="SET NULL", use_alter=True,
            name="fk_transactions_obligation_id"
        ),
        nullable=True,
    )
    fund_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "sinking_funds.id", ondelete="SET NULL", use_alter=True,
            name="fk_transactions_fund_id"
        ),
        nullable=True,
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "goals.id", ondelete="SET NULL", use_alter=True,
            name="fk_transactions_goal_id"
        ),
        nullable=True,
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "businesses.id", ondelete="SET NULL", use_alter=True,
            name="fk_transactions_business_id"
        ),
        nullable=True,
    )
    giving_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "giving_records.id", ondelete="SET NULL", use_alter=True,
            name="fk_transactions_giving_record_id"
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="cleared")
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    import_source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
