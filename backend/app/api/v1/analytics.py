from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.schemas.analytics import HealthOut, ReportOut, SnapshotOut
from app.services.analytics import (
    annual_report,
    freeze_current_snapshot,
    giving_report,
    insights_payload,
    list_snapshots,
    monthly_report,
    quarterly_report,
)
from app.services.health import household_health

router = APIRouter(tags=["analytics"])


@router.get("/financial-health", response_model=HealthOut)
def get_financial_health(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    payload = household_health(db, ctx.household)
    db.commit()
    return payload


@router.get("/financial-health/explain", response_model=HealthOut)
def explain_financial_health(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    payload = household_health(db, ctx.household)
    db.commit()
    return payload


@router.get("/insights")
def get_insights(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    payload = insights_payload(db, ctx.household)
    db.commit()
    return payload


@router.get("/snapshots", response_model=list[SnapshotOut])
def get_snapshots(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return list_snapshots(db, ctx.household.id)


@router.post("/snapshots", response_model=SnapshotOut, status_code=201)
def post_snapshot(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = freeze_current_snapshot(db, ctx.household)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports/monthly", response_model=ReportOut)
def get_monthly_report(
    period: date | None = Query(default=None),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    row = monthly_report(db, ctx.household, period)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports/quarterly", response_model=ReportOut)
def get_quarterly_report(
    year: int = Query(default=None),
    quarter: int = Query(default=None, ge=1, le=4),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    today = date.today()
    report_year = year or today.year
    report_quarter = quarter or ((today.month - 1) // 3 + 1)
    row = quarterly_report(db, ctx.household, report_year, report_quarter)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports/annual", response_model=ReportOut)
def get_annual_report(
    year: int = Query(default=None),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    row = annual_report(db, ctx.household, year or date.today().year)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports/giving", response_model=ReportOut)
def get_giving_report(
    year: int = Query(default=None),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    row = giving_report(db, ctx.household, year or date.today().year)
    db.commit()
    db.refresh(row)
    return row
