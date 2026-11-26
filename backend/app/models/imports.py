import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="completed")
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImportMailbox(Base):
    __tablename__ = "import_mailboxes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), unique=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class StatementExtractionTask(Base):
    __tablename__ = "statement_extraction_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    import_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_jobs.id", ondelete="CASCADE"), unique=True
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(200))
    suffix: Mapped[str] = mapped_column(String(10))
    account_section: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
