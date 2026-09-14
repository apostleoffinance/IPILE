"""Financial health score. Deterministic. Visible weights. Never use float."""

from dataclasses import dataclass
from decimal import Decimal

from app.money import quantize_money

WEIGHTS = {
    "cash_flow": Decimal("20"),
    "obligation_coverage": Decimal("20"),
    "emergency_readiness": Decimal("15"),
    "debt_health": Decimal("15"),
    "savings_discipline": Decimal("10"),
    "investment_discipline": Decimal("10"),
    "budget_discipline": Decimal("10"),
}

LABELS = (
    (Decimal("80"), "Healthy"),
    (Decimal("60"), "Watch"),
    (Decimal("40"), "Strained"),
    (Decimal("0"), "Critical"),
)


def clamp01(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0")
    if value > 1:
        return Decimal("1")
    return value


def health_label(score: Decimal) -> str:
    score = quantize_money(score)
    for threshold, label in LABELS:
        if score >= threshold:
            return label
    return "Critical"


@dataclass(frozen=True)
class HealthComponent:
    key: str
    weight: Decimal
    points: Decimal
    inputs: dict[str, Decimal | int | bool | str]


@dataclass(frozen=True)
class HealthResult:
    score: Decimal
    label: str
    components: list[HealthComponent]

    def points_total(self) -> Decimal:
        return quantize_money(sum((row.points for row in self.components), Decimal("0.00")))


def cash_flow_score(recognized_income: Decimal, period_surplus: Decimal) -> HealthComponent:
    income = quantize_money(recognized_income)
    surplus = quantize_money(period_surplus)
    if income == 0 and surplus <= 0:
        points = Decimal("0.00")
        ratio = Decimal("0.00")
    elif income == 0 and surplus > 0:
        points = Decimal("10.00")
        ratio = Decimal("0.00")
    else:
        ratio = quantize_money(surplus / income)
        points = quantize_money(clamp01(ratio / Decimal("0.10")) * WEIGHTS["cash_flow"])
    return HealthComponent(
        "cash_flow",
        WEIGHTS["cash_flow"],
        points,
        {"recognized_income": income, "period_surplus": surplus, "surplus_ratio": ratio},
    )


def obligation_coverage_score(funded_due_90: Decimal, due_90: Decimal) -> HealthComponent:
    funded = quantize_money(funded_due_90)
    due = quantize_money(due_90)
    if due == 0:
        coverage = Decimal("1.00")
        points = WEIGHTS["obligation_coverage"]
    else:
        coverage = quantize_money(funded / due)
        points = quantize_money(clamp01(coverage) * WEIGHTS["obligation_coverage"])
    return HealthComponent(
        "obligation_coverage",
        WEIGHTS["obligation_coverage"],
        points,
        {"funded_due_90": funded, "due_90": due, "coverage": coverage},
    )


def emergency_readiness_score(
    emergency_balance: Decimal, monthly_essentials: Decimal
) -> HealthComponent:
    emergency = quantize_money(emergency_balance)
    essentials = quantize_money(monthly_essentials)
    if essentials == 0:
        months = Decimal("3.00")
        points = WEIGHTS["emergency_readiness"]
    else:
        months = emergency / essentials
        points = quantize_money(clamp01(months / Decimal("3")) * WEIGHTS["emergency_readiness"])
        months = quantize_money(months)
    return HealthComponent(
        "emergency_readiness",
        WEIGHTS["emergency_readiness"],
        points,
        {
            "emergency_balance": emergency,
            "monthly_essentials": essentials,
            "months": months,
        },
    )


def debt_health_score(
    total_liabilities: Decimal,
    total_assets: Decimal,
    missed_debt_payment: bool,
) -> HealthComponent:
    debt = quantize_money(total_liabilities)
    assets = quantize_money(total_assets)
    if debt == 0:
        points = WEIGHTS["debt_health"]
        dta = Decimal("0.00")
        leverage = Decimal("1.00")
        missed = Decimal("1")
    else:
        dta = quantize_money(debt / max(assets, Decimal("1.00")))
        leverage = clamp01(Decimal("1") - dta / Decimal("0.40"))
        missed = Decimal("0") if missed_debt_payment else Decimal("1")
        mix = Decimal("0.7") * leverage + Decimal("0.3") * missed
        points = quantize_money(mix * WEIGHTS["debt_health"])
    return HealthComponent(
        "debt_health",
        WEIGHTS["debt_health"],
        points,
        {
            "total_liabilities": debt,
            "total_assets": assets,
            "debt_to_asset": dta,
            "leverage": quantize_money(leverage),
            "missed_debt_payment": missed_debt_payment,
        },
    )


def discipline_score(key: str, planned: Decimal, actual: Decimal) -> HealthComponent:
    planned = quantize_money(planned)
    actual = quantize_money(actual)
    if planned == 0 and actual >= 0:
        ratio = Decimal("1.00")
        points = WEIGHTS[key]
    elif planned == 0:
        ratio = Decimal("0.00")
        points = Decimal("0.00")
    else:
        ratio = quantize_money(actual / planned)
        points = quantize_money(clamp01(ratio) * WEIGHTS[key])
    return HealthComponent(
        key,
        WEIGHTS[key],
        points,
        {"planned": planned, "actual": actual, "ratio": ratio},
    )


def budget_discipline_score(
    categories_ok: int,
    category_count: int,
    total_overspend: Decimal,
    total_allocated: Decimal,
) -> HealthComponent:
    allocated = quantize_money(total_allocated)
    overspend = quantize_money(total_overspend)
    if category_count == 0:
        ok_ratio = Decimal("1.00")
    else:
        ok_ratio = quantize_money(Decimal(categories_ok) / Decimal(category_count))
    if allocated == 0:
        severity = Decimal("0.00") if overspend == 0 else Decimal("1.00")
    else:
        severity = min(Decimal("1.00"), quantize_money(overspend / allocated))
    points = quantize_money(
        (Decimal("0.7") * ok_ratio + Decimal("0.3") * (Decimal("1") - severity))
        * WEIGHTS["budget_discipline"]
    )
    return HealthComponent(
        "budget_discipline",
        WEIGHTS["budget_discipline"],
        points,
        {
            "categories_ok": categories_ok,
            "category_count": category_count,
            "ok_ratio": ok_ratio,
            "total_overspend": overspend,
            "total_allocated": allocated,
            "overspend_severity": severity,
        },
    )


def compute_health(
    *,
    recognized_income: Decimal,
    period_surplus: Decimal,
    funded_due_90: Decimal,
    due_90: Decimal,
    emergency_balance: Decimal,
    monthly_essentials: Decimal,
    total_liabilities: Decimal,
    total_assets: Decimal,
    missed_debt_payment: bool,
    planned_savings: Decimal,
    actual_savings: Decimal,
    planned_investment: Decimal,
    actual_investment: Decimal,
    categories_ok: int,
    category_count: int,
    total_overspend: Decimal,
    total_allocated: Decimal,
) -> HealthResult:
    components = [
        cash_flow_score(recognized_income, period_surplus),
        obligation_coverage_score(funded_due_90, due_90),
        emergency_readiness_score(emergency_balance, monthly_essentials),
        debt_health_score(total_liabilities, total_assets, missed_debt_payment),
        discipline_score("savings_discipline", planned_savings, actual_savings),
        discipline_score("investment_discipline", planned_investment, actual_investment),
        budget_discipline_score(categories_ok, category_count, total_overspend, total_allocated),
    ]
    score = quantize_money(sum((row.points for row in components), Decimal("0.00")))
    return HealthResult(score=score, label=health_label(score), components=components)
