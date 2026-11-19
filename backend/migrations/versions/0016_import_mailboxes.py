"""household email import mailboxes

Revision ID: 0016_import_mailboxes
Revises: 0015_phase15
Create Date: 2026-11-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_import_mailboxes"
down_revision: Union[str, None] = "0015_phase15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("import_jobs", "status", existing_type=sa.String(length=20), type_=sa.String(length=30), existing_nullable=False)
    op.create_table(
        "import_mailboxes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("household_id", name="uq_import_mailboxes_household_id"),
        sa.UniqueConstraint("token_hash", name="uq_import_mailboxes_token_hash"),
    )
    op.create_index("ix_import_mailboxes_household_id", "import_mailboxes", ["household_id"])
    op.create_index("ix_import_mailboxes_token_hash", "import_mailboxes", ["token_hash"])


def downgrade() -> None:
    op.alter_column("import_jobs", "status", existing_type=sa.String(length=30), type_=sa.String(length=20), existing_nullable=False)
    op.drop_index("ix_import_mailboxes_token_hash", table_name="import_mailboxes")
    op.drop_index("ix_import_mailboxes_household_id", table_name="import_mailboxes")
    op.drop_table("import_mailboxes")
