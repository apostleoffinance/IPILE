"""simulations and simulation runs

Revision ID: 0010_simulation
Revises: 0009_analytics
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_simulation"
down_revision: Union[str, None] = "0009_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default="Scenario"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_simulations_household_id", "simulations", ["household_id"])
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("simulation_id", sa.Uuid(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_simulation_runs_household_id", "simulation_runs", ["household_id"])


def downgrade() -> None:
    op.drop_index("ix_simulation_runs_household_id", table_name="simulation_runs")
    op.drop_table("simulation_runs")
    op.drop_index("ix_simulations_household_id", table_name="simulations")
    op.drop_table("simulations")
