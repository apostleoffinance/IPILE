import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Obligation(Base):
    __tablename__ = "obligations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    next_due_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    sinking_fund: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_allocate: Mapped[bool] = mapped_column(Boolean, default=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    beneficiary_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    beneficiary_member_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("household_members.id", ondelete="SET NULL"), nullable=True
    )
    fund_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "sinking_funds.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_obligations_fund_id",
        ),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ObligationOccurrence(Base):
    __tablename__ = "obligation_occurrences"
    __table_args__ = (
        UniqueConstraint("obligation_id", "due_date", name="uq_obligation_occurrences_due"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    obligation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("obligations.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    funded_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "transactions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_occurrences_transaction_id",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
