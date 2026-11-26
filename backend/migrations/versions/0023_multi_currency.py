"""Add auditable exchange rates and transaction conversion metadata.

Revision ID: 0023_multi_currency
Revises: 0022_bank_reconciliation
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_multi_currency"
down_revision: Union[str, None] = "0022_bank_reconciliation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("quote_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(24, 12), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rate > 0", name="ck_exchange_rates_positive_rate"),
        sa.CheckConstraint("base_currency <> quote_currency", name="ck_exchange_rates_distinct_currencies"),
        sa.UniqueConstraint("household_id", "base_currency", "quote_currency", "rate_date", "source",
                            name="uq_exchange_rates_household_pair_date_source"),
    )
    op.create_index("ix_exchange_rates_household_id", "exchange_rates", ["household_id"])
    op.create_index("ix_exchange_rates_pair_date", "exchange_rates",
                    ["household_id", "base_currency", "quote_currency", "rate_date"])

    op.add_column("giving_records", sa.Column("base_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("giving_records", sa.Column("base_currency", sa.String(3), nullable=True))
    op.execute("""
        UPDATE giving_records AS g
        SET currency = COALESCE(a.currency, h.base_currency, 'NGN'),
            base_currency = COALESCE(h.base_currency, 'NGN'),
            base_amount = CASE
                WHEN COALESCE(a.currency, h.base_currency, 'NGN') = COALESCE(h.base_currency, 'NGN')
                THEN g.amount ELSE NULL END
        FROM accounts AS a, households AS h
        WHERE g.account_id = a.id AND g.household_id = h.id
    """)

    # Existing transactions retain their original amounts. Their currency is
    # aligned to the account's existing currency (legacy default remains NGN).
    op.add_column("transactions", sa.Column("base_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("transactions", sa.Column("base_currency", sa.String(3), nullable=True))
    op.add_column("transactions", sa.Column("exchange_rate", sa.Numeric(24, 12), nullable=True))
    op.add_column("transactions", sa.Column("exchange_rate_date", sa.Date(), nullable=True))
    op.add_column("transactions", sa.Column("exchange_rate_source", sa.String(40), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_currency", sa.String(3), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_base_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_exchange_rate", sa.Numeric(24, 12), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_exchange_rate_date", sa.Date(), nullable=True))
    op.add_column("transactions", sa.Column("counterparty_exchange_rate_source", sa.String(40), nullable=True))
    op.execute("""
        UPDATE transactions AS t
        SET currency = COALESCE(a.currency, h.base_currency, 'NGN'),
            base_currency = COALESCE(h.base_currency, 'NGN'),
            base_amount = CASE
                WHEN COALESCE(a.currency, h.base_currency, 'NGN') = COALESCE(h.base_currency, 'NGN')
                THEN t.amount ELSE NULL END
        FROM accounts AS a, households AS h
        WHERE t.account_id = a.id AND t.household_id = h.id
    """)


def downgrade() -> None:
    op.drop_column("giving_records", "base_currency")
    op.drop_column("giving_records", "base_amount")
    op.drop_column("transactions", "counterparty_exchange_rate_source")
    op.drop_column("transactions", "counterparty_exchange_rate_date")
    op.drop_column("transactions", "counterparty_exchange_rate")
    op.drop_column("transactions", "counterparty_base_amount")
    op.drop_column("transactions", "counterparty_currency")
    op.drop_column("transactions", "counterparty_amount")
    op.drop_column("transactions", "exchange_rate_source")
    op.drop_column("transactions", "exchange_rate_date")
    op.drop_column("transactions", "exchange_rate")
    op.drop_column("transactions", "base_currency")
    op.drop_column("transactions", "base_amount")
    op.drop_index("ix_exchange_rates_pair_date", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_household_id", table_name="exchange_rates")
    op.drop_table("exchange_rates")
