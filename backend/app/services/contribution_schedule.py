from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal


def _due_dates(agreement, through: date) -> list[date]:
    if agreement.status in {"cancelled", "completed"}:
        through = min(through, date.today())
    start = agreement.start_date
    end = min(through, agreement.end_date) if agreement.end_date else through
    if end < start:
        return []
    if agreement.cadence == "one_off":
        return [start]
    if agreement.cadence in {"weekly", "biweekly"}:
        step = 7 if agreement.cadence == "weekly" else 14
        dates = []
        due = start
        while due <= end and len(dates) < 600:
            dates.append(due)
            due += timedelta(days=step)
        return dates
    month_step = {"monthly": 1, "quarterly": 3, "annually": 12}[agreement.cadence]
    due_day = agreement.due_day or start.day
    dates = []
    year, month = start.year, start.month
    while len(dates) < 600:
        due = date(year, month, min(due_day, monthrange(year, month)[1]))
        if start <= due <= end:
            dates.append(due)
        if due > end:
            break
        month_index = year * 12 + month - 1 + month_step
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
    return dates


def build_contribution_schedule(
    agreements,
    records_by_agreement: dict,
    *,
    from_date: date,
    to_date: date,
    today: date | None = None,
) -> list[dict]:
    today = today or date.today()
    rows = []
    for agreement in agreements:
        due_dates = _due_dates(agreement, to_date)
        paid_by_due = {due: Decimal("0.00") for due in due_dates}
        records = sorted(
            records_by_agreement.get(agreement.id, []),
            key=lambda record: (record.contributed_on, record.created_at),
        )
        for record in records:
            remaining = Decimal(record.amount)
            for due in due_dates:
                outstanding = max(Decimal("0.00"), Decimal(agreement.amount) - paid_by_due[due])
                if outstanding == 0:
                    continue
                applied = min(outstanding, remaining)
                paid_by_due[due] += applied
                remaining -= applied
                if remaining == 0:
                    break
        for due in due_dates:
            if due < from_date:
                continue
            expected = Decimal(agreement.amount)
            paid = paid_by_due[due]
            outstanding = max(Decimal("0.00"), expected - paid)
            if paid >= expected:
                status = "paid"
            elif paid > 0:
                status = "partial"
            elif due < today:
                status = "overdue"
            else:
                status = "upcoming"
            rows.append({
                "agreement_id": agreement.id,
                "member_id": agreement.member_id,
                "name": agreement.name,
                "due_date": due,
                "currency": agreement.currency,
                "expected_amount": expected,
                "paid_amount": paid,
                "outstanding_amount": outstanding,
                "status": status,
            })
    return sorted(rows, key=lambda row: (row["due_date"], str(row["agreement_id"])))
