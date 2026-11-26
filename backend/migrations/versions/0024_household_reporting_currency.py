"""Add household reporting currency without changing native ledger values.

Revision ID: 0024_household_reporting_currency
Revises: 0023_multi_currency
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_household_reporting_currency"
down_revision: Union[str, None] = "0023_multi_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "households",
        sa.Column("reporting_currency", sa.String(length=3), nullable=True),
    )
    op.execute("UPDATE households SET reporting_currency = base_currency WHERE reporting_currency IS NULL")
    op.alter_column("households", "reporting_currency", nullable=False, server_default="NGN")


def downgrade() -> None:
    op.drop_column("households", "reporting_currency")
