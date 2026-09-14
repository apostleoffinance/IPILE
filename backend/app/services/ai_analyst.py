from datetime import date

from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.fund import SinkingFund
from app.models.household import Household
from app.models.obligation import Obligation
from app.money import format_money
from app.services.ai_engine import ModelClient, explain
from app.services.budgets import serialize_budget
from app.services.funds import serialize_fund
from app.services.health import household_health
from app.services.obligations import serialize_obligation
from app.services.safe_to_spend import compute_safe_to_spend
from app.services.wealth import household_net_worth


def verified_payload(db: Session, household: Household, today: date | None = None) -> dict:
    today = today or date.today()
    health = household_health(db, household, today)
    sts = compute_safe_to_spend(db, household, today=today)
    wealth = household_net_worth(db, household)
    budgets = (
        db.query(Budget)
        .filter(
            Budget.household_id == household.id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
        )
        .all()
    )
    budget_rows = []
    for budget in budgets:
        snap = serialize_budget(db, budget)
        budget_rows.append(
            {
                "name": snap.name,
                "allocated_total": format_money(snap.allocated_total),
                "spent_total": format_money(snap.spent_total),
                "remaining_total": format_money(snap.remaining_total),
            }
        )
    obligations = (
        db.query(Obligation)
        .filter(Obligation.household_id == household.id, Obligation.deleted_at.is_(None))
        .all()
    )
    obligation_rows = []
    for obligation in obligations:
        snap = serialize_obligation(db, obligation)
        next_occ = snap.next_occurrence
        obligation_rows.append(
            {
                "name": snap.name,
                "amount": format_money(snap.amount),
                "next_due_date": snap.next_due_date.isoformat() if snap.next_due_date else None,
                "coverage": next_occ.coverage if next_occ else "1.00",
                "coverage_label": next_occ.coverage_label if next_occ else "funded",
            }
        )
    funds = (
        db.query(SinkingFund)
        .filter(SinkingFund.household_id == household.id, SinkingFund.deleted_at.is_(None))
        .all()
    )
    fund_rows = []
    for fund in funds:
        snap = serialize_fund(db, fund, today=today)
        fund_rows.append(
            {
                "name": snap.name,
                "current_amount": format_money(fund.current_amount),
                "target_amount": format_money(fund.target_amount),
                "progress": snap.progress,
            }
        )
    return {
        "health": {
            "score": health["score"],
            "label": health["label"],
        },
        "safe_to_spend": {
            "current": format_money(sts.current),
            "period": format_money(sts.period),
            "forecast": format_money(sts.forecast),
        },
        "wealth": {
            "net_worth": format_money(wealth.net_worth),
            "emergency_fund": format_money(wealth.emergency_fund),
            "debt": format_money(wealth.debt),
        },
        "budgets": budget_rows,
        "obligations": obligation_rows,
        "funds": fund_rows,
        "as_of": today.isoformat(),
    }


def explain_household(
    db: Session,
    household: Household,
    *,
    model: ModelClient | None = None,
    today: date | None = None,
) -> dict:
    payload = verified_payload(db, household, today)
    text = explain(payload, model=model)
    return {"explanation": text, "payload": payload, "source": "verified_engines"}
