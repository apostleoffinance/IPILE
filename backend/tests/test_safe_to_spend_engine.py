from decimal import Decimal
from pathlib import Path

from app.services.safe_to_spend_engine import (
    current_safe_to_spend,
    forecast_safe_to_spend,
    period_safe_to_spend,
    purchase_check,
)


def test_current_sts_excludes_protected_and_pending() -> None:
    current = current_safe_to_spend(
        Decimal("1400000.00"),
        Decimal("850000.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )
    assert current == Decimal("550000.00")
    with_protected = current_safe_to_spend(
        Decimal("1400000.00"),
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("150000.00"),
    )
    assert with_protected == Decimal("1250000.00")


def test_purchase_one_eighty_against_five_fifty_is_affordable() -> None:
    result = purchase_check(Decimal("180000.00"), Decimal("550000.00"), Decimal("90000.00"))
    assert result.affordable is True
    assert result.severity == "healthy"
    assert result.remaining_current_sts == Decimal("370000.00")
    assert result.buffer_breached is False
    assert result.recommended_action == "proceed"


def test_purchase_buffer_breach_warns() -> None:
    result = purchase_check(Decimal("500000.00"), Decimal("550000.00"), Decimal("90000.00"))
    assert result.affordable is True
    assert result.severity == "warning"
    assert result.buffer_breached is True
    assert result.remaining_current_sts == Decimal("50000.00")
    assert result.recommended_action == "delay / reduce / use surplus"


def test_purchase_over_sts_is_critical() -> None:
    result = purchase_check(Decimal("600000.00"), Decimal("550000.00"), Decimal("90000.00"))
    assert result.affordable is False
    assert result.severity == "critical"
    assert result.remaining_current_sts == Decimal("-50000.00")


def test_period_and_forecast_formulas() -> None:
    period = period_safe_to_spend(
        Decimal("550000.00"),
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )
    assert period == Decimal("550000.00")
    forecast = forecast_safe_to_spend(
        Decimal("1400000.00"),
        Decimal("850000.00"),
        Decimal("90000.00"),
    )
    assert forecast == Decimal("460000.00")


def test_sts_engine_has_no_religious_hardcoding() -> None:
    text = Path("app/services/safe_to_spend_engine.py").read_text().lower()
    for banned in ("tithe", "christian", "church", "religion"):
        assert banned not in text
