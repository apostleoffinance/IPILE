from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_contribution_agreement_and_record_are_scoped(client: TestClient) -> None:
    register(client, "contribution-owner@example.com")
    member = client.post("/api/v1/members", json={"display_name": "Ada", "role": "member"})
    assert member.status_code == 201, member.text
    agreement = client.post("/api/v1/contributions", json={
        "member_id": member.json()["id"], "name": "Monthly household contribution",
        "amount": "50000.00", "currency": "NGN", "cadence": "monthly",
        "due_day": 5, "start_date": "2026-11-01",
    })
    assert agreement.status_code == 201, agreement.text
    record = client.post(f"/api/v1/contributions/{agreement.json()['id']}/records", json={
        "amount": "25000.00", "contributed_on": "2026-11-05", "note": "Part payment",
    })
    assert record.status_code == 201, record.text
    rows = client.get(f"/api/v1/contributions/{agreement.json()['id']}/records")
    assert rows.status_code == 200 and len(rows.json()) == 1
    assert Decimal(rows.json()[0]["amount"]) == Decimal("25000.00")


def test_contribution_agreement_rejects_invalid_dates_and_foreign_member(client: TestClient) -> None:
    register(client, "contribution-validation@example.com")
    invalid = client.post("/api/v1/contributions", json={
        "member_id": "00000000-0000-0000-0000-000000000000", "name": "Bad plan",
        "amount": "100.00", "cadence": "monthly", "due_day": 5,
        "start_date": "2026-12-01", "end_date": "2026-11-01",
    })
    assert invalid.status_code == 422
    foreign = client.post("/api/v1/contributions", json={
        "member_id": "00000000-0000-0000-0000-000000000000", "name": "Foreign plan",
        "amount": "100.00", "cadence": "monthly", "due_day": 5,
        "start_date": "2026-11-01",
    })
    assert foreign.status_code == 404
