from decimal import Decimal

from app.services.business_engine import BusinessLine, compute_pnl, family_return


def test_family_invested_and_return_formulas() -> None:
    lines = [
        BusinessLine("capital_contribution", Decimal("200000.00")),
        BusinessLine("revenue", Decimal("80000.00")),
        BusinessLine("expense", Decimal("20000.00")),
        BusinessLine("payroll", Decimal("10000.00")),
        BusinessLine("withdrawal", Decimal("15000.00")),
    ]
    result = compute_pnl(lines)
    assert result.family_invested == Decimal("200000.00")
    assert result.family_withdrawn == Decimal("15000.00")
    assert result.revenue == Decimal("80000.00")
    assert result.expenses == Decimal("30000.00")
    assert result.profit == Decimal("50000.00")
    assert result.current_business_equity == Decimal("235000.00")
    assert result.family_return == Decimal("50000.00")
    assert family_return(
        Decimal("15000.00"),
        Decimal("235000.00"),
        Decimal("200000.00"),
    ) == Decimal("50000.00")


def test_account_balance_is_equity_source_of_truth() -> None:
    lines = [BusinessLine("capital_contribution", Decimal("200000.00"))]
    result = compute_pnl(lines, Decimal("200000.00"))
    assert result.current_business_equity == Decimal("200000.00")
    assert result.family_return == Decimal("0.00")
