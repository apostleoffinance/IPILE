from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import billing


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flushed = True


def test_paid_plan_cannot_be_activated_without_payment_integration(monkeypatch) -> None:
    household = SimpleNamespace(
        id=uuid4(),
        plan="pilot",
        billing_status="active",
    )
    db = FakeSession()

    with pytest.raises(ValueError, match="Paid plans are unavailable"):
        billing.change_plan(
            db,
            household,
            user_id=uuid4(),
            plan="family",
        )

    assert household.plan == "pilot"
    assert household.billing_status == "active"
    assert db.added == []
    assert db.flushed is False


def test_pilot_plan_remains_available(monkeypatch) -> None:
    household = SimpleNamespace(
        id=uuid4(),
        plan="family",
        billing_status="active",
    )
    db = FakeSession()
    audit_calls = []
    monkeypatch.setattr(
        billing,
        "write_audit",
        lambda *args, **kwargs: audit_calls.append((args, kwargs)),
    )

    result = billing.change_plan(
        db,
        household,
        user_id=uuid4(),
        plan="pilot",
    )

    assert result is household
    assert household.plan == "pilot"
    assert household.billing_status == "active"
    assert db.added == [household]
    assert db.flushed is True
    assert len(audit_calls) == 1


def test_unknown_plan_is_rejected() -> None:
    household = SimpleNamespace(
        id=uuid4(),
        plan="pilot",
        billing_status="active",
    )

    with pytest.raises(ValueError, match="Unknown plan"):
        billing.change_plan(
            FakeSession(),
            household,
            user_id=uuid4(),
            plan="enterprise",
        )
