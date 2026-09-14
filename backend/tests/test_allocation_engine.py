from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.services.allocation_engine import AllocationRuleSpec, allocate


def rule(
    name: str,
    kind: str,
    *,
    basis: str = "recognized_income",
    rate: str | None = None,
    amount: str | None = None,
    priority: int,
    mandatory: bool = True,
    destination: str,
) -> AllocationRuleSpec:
    return AllocationRuleSpec(
        id=None,
        name=name,
        type=kind,
        basis=basis,
        rate=Decimal(rate) if rate is not None else None,
        amount=Decimal(amount) if amount is not None else None,
        priority=priority,
        mandatory=mandatory,
        destination_type=destination,
        destination_id=None,
        income_source_id=None,
    )


SEED_RULES = [
    rule("Giving share", "percentage", rate="0.10", priority=0, destination="giving"),
    rule("Parents' stipend", "fixed", amount="100000.00", priority=1, destination="obligation"),
    rule("University fund", "fixed", amount="150000.00", priority=2, destination="fund"),
    rule("Parents' rent fund", "fixed", amount="50000.00", priority=3, destination="fund"),
    rule("Household essentials", "fixed", amount="670000.00", priority=4, destination="budget"),
    rule("Emergency fund", "fixed", amount="150000.00", priority=5, destination="account"),
    rule("Investments", "fixed", amount="200000.00", priority=6, destination="account"),
    rule("Personal allowances", "fixed", amount="140000.00", priority=7, destination="budget"),
    rule("Additional giving", "fixed", amount="50000.00", priority=8, destination="giving"),
    rule("Buffer", "fixed", amount="90000.00", priority=9, destination="account"),
    rule(
        "Family surplus",
        "remainder",
        basis="remaining",
        priority=10,
        mandatory=False,
        destination="account",
    ),
]


SPEC_TABLE = {
    "Giving share": "200000.00",
    "Parents' stipend": "100000.00",
    "University fund": "150000.00",
    "Parents' rent fund": "50000.00",
    "Household essentials": "670000.00",
    "Emergency fund": "150000.00",
    "Investments": "200000.00",
    "Personal allowances": "140000.00",
    "Additional giving": "50000.00",
    "Buffer": "90000.00",
    "Family surplus": "200000.00",
}


def test_two_million_matches_spec_table() -> None:
    result = allocate(Decimal("2000000.00"), SEED_RULES)
    amounts = {line.name: f"{line.amount:.2f}" for line in result.lines}
    assert amounts == SPEC_TABLE
    assert result.total_allocated == Decimal("2000000.00")
    assert result.surplus == Decimal("0.00")
    assert result.unfunded_mandatory == ()


def test_zero_income_leaves_mandatory_unfunded() -> None:
    result = allocate(Decimal("0.00"), SEED_RULES)
    assert result.recognized_income == Decimal("0.00")
    assert result.total_allocated == Decimal("0.00")
    assert result.surplus == Decimal("0.00")
    assert all(line.amount == Decimal("0.00") for line in result.lines)
    names = {line.name for line in result.unfunded_mandatory}
    assert "Giving share" not in names
    assert names == {
        "Parents' stipend",
        "University fund",
        "Parents' rent fund",
        "Household essentials",
        "Emergency fund",
        "Investments",
        "Personal allowances",
        "Additional giving",
        "Buffer",
    }


def test_income_below_mandatory_takes_priority_order() -> None:
    result = allocate(Decimal("250000.00"), SEED_RULES)
    amounts = {line.name: line.amount for line in result.lines}
    assert amounts["Giving share"] == Decimal("25000.00")
    assert amounts["Parents' stipend"] == Decimal("100000.00")
    assert amounts["University fund"] == Decimal("125000.00")
    assert amounts["Parents' rent fund"] == Decimal("0.00")
    assert amounts["Family surplus"] == Decimal("0.00")
    unfunded = {line.name: line.requested for line in result.unfunded_mandatory}
    assert unfunded["University fund"] == Decimal("150000.00")
    assert "Parents' rent fund" in unfunded
    assert result.surplus == Decimal("0.00")


def test_remainder_absorbs_rounding_leftover() -> None:
    rules = [
        rule("Share", "percentage", rate="0.3333", priority=0, destination="giving"),
        rule(
            "Leftover",
            "remainder",
            basis="remaining",
            priority=1,
            mandatory=False,
            destination="account",
        ),
    ]
    result = allocate(Decimal("100.00"), rules)
    assert result.lines[0].amount == Decimal("33.33")
    assert result.lines[1].amount == Decimal("66.67")
    assert result.surplus == Decimal("0.00")
    assert result.total_allocated == Decimal("100.00")


def test_engine_has_no_religious_hardcoding() -> None:
    text = Path("app/services/allocation_engine.py").read_text().lower()
    for banned in ("tithe", "christian", "church", "religion", "islam", "zakat"):
        assert banned not in text


def test_specific_source_uses_that_source_pool() -> None:
    source_id = UUID("11111111-1111-1111-1111-111111111111")
    spec = AllocationRuleSpec(
        id=None,
        name="Source share",
        type="percentage",
        basis="specific_source",
        rate=Decimal("0.50"),
        amount=None,
        priority=0,
        mandatory=True,
        destination_type="giving",
        income_source_id=source_id,
    )
    result = allocate(
        Decimal("1000.00"),
        [spec],
        {source_id: Decimal("200.00")},
    )
    assert result.lines[0].amount == Decimal("100.00")
    assert result.surplus == Decimal("900.00")
