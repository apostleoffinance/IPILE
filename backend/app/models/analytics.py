import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (
        UniqueConstraint("household_id", "period_start", name="uq_financial_snapshots_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    as_of: Mapped[date] = mapped_column(Date)
    income: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    expenses: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    savings: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    investments: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    giving: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    debt_reduction: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    surplus: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    health_score: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FinancialScore(Base):
    __tablename__ = "financial_scores"
    __table_args__ = (
        UniqueConstraint("household_id", "period_start", name="uq_financial_scores_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    score: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    label: Mapped[str] = mapped_column(String(20), default="Critical")
    components: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("household_id", "kind", "period_start", name="uq_reports_kind_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
