"""Add transactional statement extraction dispatch outbox."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_statement_extraction_outbox"
down_revision: Union[str, None] = "0026_statement_extraction_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "statement_extraction_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "task_id", sa.Uuid(),
            sa.ForeignKey("statement_extraction_tasks.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_statement_extraction_outbox_task_id", "statement_extraction_outbox", ["task_id"])
    op.create_index("ix_statement_extraction_outbox_status", "statement_extraction_outbox", ["status"])


def downgrade() -> None:
    op.drop_index("ix_statement_extraction_outbox_status", table_name="statement_extraction_outbox")
    op.drop_index("ix_statement_extraction_outbox_task_id", table_name="statement_extraction_outbox")
    op.drop_table("statement_extraction_outbox")
