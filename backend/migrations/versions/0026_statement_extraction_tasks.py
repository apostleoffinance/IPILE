"""Add durable background statement extraction tasks."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_statement_extraction_tasks"
down_revision: Union[str, None] = "0025_gmail_alert_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "statement_extraction_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "import_job_id",
            sa.Uuid(),
            sa.ForeignKey("import_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "household_id",
            sa.Uuid(),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("suffix", sa.String(10), nullable=False),
        sa.Column("account_section", sa.String(120), nullable=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_statement_extraction_tasks_import_job_id",
        "statement_extraction_tasks",
        ["import_job_id"],
    )
    op.create_index(
        "ix_statement_extraction_tasks_household_id",
        "statement_extraction_tasks",
        ["household_id"],
    )
    op.create_index(
        "ix_statement_extraction_tasks_account_id",
        "statement_extraction_tasks",
        ["account_id"],
    )
    op.create_index(
        "ix_statement_extraction_tasks_status",
        "statement_extraction_tasks",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_statement_extraction_tasks_status", table_name="statement_extraction_tasks")
    op.drop_index("ix_statement_extraction_tasks_account_id", table_name="statement_extraction_tasks")
    op.drop_index("ix_statement_extraction_tasks_household_id", table_name="statement_extraction_tasks")
    op.drop_index("ix_statement_extraction_tasks_import_job_id", table_name="statement_extraction_tasks")
    op.drop_table("statement_extraction_tasks")
