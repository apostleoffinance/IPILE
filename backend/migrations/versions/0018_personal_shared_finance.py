"""personal and shared finance ownership boundaries

Revision ID: 0018_personal_shared_finance
Revises: 0017_contributions
Create Date: 2026-11-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_personal_shared_finance"
down_revision: Union[str, None] = "0017_contributions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("access_scope", sa.String(20), nullable=False, server_default="shared"))
    op.add_column("transactions", sa.Column("access_scope", sa.String(20), nullable=False, server_default="shared"))
    op.create_check_constraint("ck_accounts_access_scope", "accounts", "access_scope IN ('shared', 'personal')")
    op.create_check_constraint("ck_transactions_access_scope", "transactions", "access_scope IN ('shared', 'personal')")
    op.create_check_constraint("ck_accounts_personal_owner", "accounts", "(access_scope = 'shared' AND owner_member_id IS NULL) OR (access_scope = 'personal' AND owner_member_id IS NOT NULL)")
    op.create_check_constraint("ck_transactions_personal_owner", "transactions", "(access_scope = 'shared' AND member_id IS NULL) OR (access_scope = 'personal' AND member_id IS NOT NULL)")
    op.create_index("ix_accounts_household_scope_owner", "accounts", ["household_id", "access_scope", "owner_member_id"])
    op.create_index("ix_transactions_household_scope_owner", "transactions", ["household_id", "access_scope", "member_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_household_scope_owner", table_name="transactions")
    op.drop_index("ix_accounts_household_scope_owner", table_name="accounts")
    op.drop_constraint("ck_transactions_personal_owner", "transactions", type_="check")
    op.drop_constraint("ck_accounts_personal_owner", "accounts", type_="check")
    op.drop_constraint("ck_transactions_access_scope", "transactions", type_="check")
    op.drop_constraint("ck_accounts_access_scope", "accounts", type_="check")
    op.drop_column("transactions", "access_scope")
    op.drop_column("accounts", "access_scope")
