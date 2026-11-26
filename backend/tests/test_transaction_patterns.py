from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.transaction_patterns import (
    detect_recurring_payments,
    detect_unusual_transactions,
)


def _transaction(*, day, amount="100.00", merchant="Netflix", tx_id=None):
    return SimpleNamespace(
        id=tx_id or uuid4(),
        account_id="account-1",
        category_id="category-1",
        currency="NGN",
        type="expense",
        status="cleared",
        deleted_at=None,
        date=day,
        amount=Decimal(amount),
        merchant=merchant,
        description=None,
    )


def test_detects_monthly_recurring_payment_with_upcoming_date():
    rows = [
        _transaction(day=date(2026, 1, 5)),
        _transaction(day=date(2026, 2, 5)),
        _transaction(day=date(2026, 3, 5)),
    ]
    found = detect_recurring_payments(rows, today=date(2026, 3, 6))
    assert len(found) == 1
    assert found[0]["code"] == "recurring_payment_upcoming"
    assert found[0]["evidence"]["frequency"] == "monthly"
    assert found[0]["evidence"]["expected_next_date"] == "2026-04-04"


def test_does_not_infer_recurring_from_only_two_transactions():
    rows = [
        _transaction(day=date(2026, 2, 5)),
        _transaction(day=date(2026, 3, 5)),
    ]
    assert detect_recurring_payments(rows, today=date(2026, 3, 6)) == []


def test_detects_unusually_large_transaction_against_payee_history():
    rows = [
        _transaction(day=date(2025, 12, 1), amount="100.00"),
        _transaction(day=date(2026, 1, 1), amount="110.00"),
        _transaction(day=date(2026, 1, 20), amount="90.00"),
        _transaction(day=date(2026, 2, 1), amount="105.00"),
        _transaction(day=date(2026, 2, 20), amount="100.00"),
        _transaction(day=date(2026, 3, 2), amount="500.00"),
    ]
    found = detect_unusual_transactions(rows, today=date(2026, 3, 6))
    assert len(found) == 1
    assert found[0]["code"] == "unusually_large_transaction"
    assert Decimal(found[0]["evidence"]["multiple"]) >= Decimal("3.0")


def test_does_not_flag_large_transaction_without_sufficient_history():
    rows = [
        _transaction(day=date(2026, 2, 1), amount="100.00"),
        _transaction(day=date(2026, 3, 2), amount="1000.00"),
    ]
    assert detect_unusual_transactions(rows, today=date(2026, 3, 6)) == []


def test_detects_annual_recurring_pattern_even_when_not_due_soon():
    rows = [
        _transaction(day=date(2024, 1, 1), amount="1200.00"),
        _transaction(day=date(2025, 1, 1), amount="1200.00"),
        _transaction(day=date(2026, 1, 1), amount="1200.00"),
    ]
    found = detect_recurring_payments(rows, today=date(2026, 1, 5))
    assert len(found) == 1
    assert found[0]["code"] == "recurring_payment_detected"
    assert found[0]["evidence"]["frequency"] == "annual"
    assert found[0]["evidence"]["expected_next_date"] == "2027-01-01"


def test_flags_a_recurring_payment_that_appears_overdue():
    rows = [
        _transaction(day=date(2025, 12, 1)),
        _transaction(day=date(2026, 1, 1)),
        _transaction(day=date(2026, 1, 31)),
    ]
    found = detect_recurring_payments(rows, today=date(2026, 3, 10))
    assert len(found) == 1
    assert found[0]["code"] == "recurring_payment_missed"
    assert found[0]["severity"] == "warning"



def test_bank_sender_domain_and_generic_alert_subject_do_not_become_payees():
    rows = [
        _transaction(day=date(2026, 1, 5), merchant="gtbank.com"),
        _transaction(day=date(2026, 2, 5), merchant="gtbank.com"),
        _transaction(day=date(2026, 3, 5), merchant="gtbank.com"),
    ]
    for row in rows:
        row.description = "Debit Alert"
    assert detect_recurring_payments(rows, today=date(2026, 3, 6)) == []
