"""Financial contribution forecast, kept separate from recognized ledger income.

Only cleared/reconciled income transactions linked to a contribution record count as
received for this forecast. Unlinked contribution records remain reported receipts,
not spendable cash. Expected amounts are projections only.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contribution import ContributionAgreement, ContributionRecord
from app.models.transaction import Transaction
from app.services.contribution_schedule import build_contribution_schedule

ACTIVE = "active"
RECOGNIZED = ("cleared", "reconciled")
ZERO = Decimal("0.00")


def contribution_forecast(
    db: Session,
    household_id: UUID,
    base_currency: str,
    *,
    today: date | None = None,
    horizon_days: int = 90,
    member_id: UUID | None = None,
) -> dict:
    """Return due-by-date expected, verified received, and outstanding amounts.

    Contributions in another currency are returned separately and never converted
    or added to the household-currency total without an FX rate.
    """
    if not 1 <= horizon_days <= 730:
        raise ValueError("horizon_days must be between 1 and 730.")
    today = today or date.today()
    end = today + timedelta(days=horizon_days)
    agreements_query = db.query(ContributionAgreement).filter(
            ContributionAgreement.household_id == household_id,
            ContributionAgreement.status == ACTIVE,
            ContributionAgreement.start_date <= end,
            (ContributionAgreement.end_date.is_(None))
            | (ContributionAgreement.end_date >= today),
        )
    if member_id is not None:
        agreements_query = agreements_query.filter(ContributionAgreement.member_id == member_id)
    agreements = agreements_query.order_by(
        ContributionAgreement.start_date, ContributionAgreement.id
    ).all()
    if not agreements:
        return {
            "currency": base_currency,
            "horizon_days": horizon_days,
            "expected": ZERO,
            "verified_received": ZERO,
            "outstanding": ZERO,
            "other_currency_outstanding": {},
            "rows": [],
        }

    ids = [row.id for row in agreements]
    # A record is verified for cash-flow forecasting only when it is attached to
    # a recognized income transaction. A manually reported receipt alone cannot
    # increase projected or current spendable cash.
    verified = (
        db.query(ContributionRecord)
        .join(Transaction, Transaction.id == ContributionRecord.transaction_id)
        .filter(
            ContributionRecord.household_id == household_id,
            ContributionRecord.agreement_id.in_(ids),
            ContributionRecord.contributed_on <= end,
            Transaction.household_id == household_id,
            Transaction.type == "income",
            Transaction.status.in_(RECOGNIZED),
            Transaction.deleted_at.is_(None),
        )
        .order_by(ContributionRecord.contributed_on, ContributionRecord.created_at)
        .all()
    )
    by_agreement: dict[UUID, list[ContributionRecord]] = defaultdict(list)
    for record in verified:
        by_agreement[record.agreement_id].append(record)

    rows = build_contribution_schedule(
        agreements,
        by_agreement,
        from_date=today,
        to_date=end,
        today=today,
    )
    expected = ZERO
    received = ZERO
    outstanding = ZERO
    other: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        currency = row["currency"].upper()
        row_expected = Decimal(row["expected_amount"])
        row_received = Decimal(row["paid_amount"])
        row_outstanding = Decimal(row["outstanding_amount"])
        if currency != base_currency.upper():
            other[currency] += row_outstanding
            continue
        expected += row_expected
        received += row_received
        outstanding += row_outstanding

    return {
        "currency": base_currency,
        "horizon_days": horizon_days,
        "expected": expected.quantize(Decimal("0.01")),
        "verified_received": received.quantize(Decimal("0.01")),
        "outstanding": outstanding.quantize(Decimal("0.01")),
        "other_currency_outstanding": {
            currency: amount.quantize(Decimal("0.01"))
            for currency, amount in sorted(other.items())
        },
        "rows": rows,
    }
