from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_members_only_see_their_own_contribution_agreements_records_and_schedule(
    client: TestClient,
) -> None:
    register(client, "contribution-scope-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "contribution-scope-a@example.com", "Member A")
    _logout(client)
    register(client, "contribution-scope-b@example.com", "Member B")
    _logout(client)

    login(client, "contribution-scope-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member A",
            "role": "member",
            "relationship": "other",
            "email": "contribution-scope-a@example.com",
        },
    ).json()
    member_b = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member B",
            "role": "member",
            "relationship": "other",
            "email": "contribution-scope-b@example.com",
        },
    ).json()

    start_date = date.today() - timedelta(days=20)
    contribution_date = date.today() - timedelta(days=5)
    agreement_a = client.post(
        "/api/v1/contributions",
        headers=headers,
        json={
            "member_id": member_a["id"],
            "name": "Member A monthly contribution",
            "amount": "1000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    agreement_b = client.post(
        "/api/v1/contributions",
        headers=headers,
        json={
            "member_id": member_b["id"],
            "name": "Member B monthly contribution",
            "amount": "500.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": start_date.day,
            "start_date": start_date.isoformat(),
        },
    )
    assert agreement_a.status_code == 201, agreement_a.text
    assert agreement_b.status_code == 201, agreement_b.text

    record = client.post(
        f"/api/v1/contributions/{agreement_a.json()['id']}/records",
        headers=headers,
        json={
            "amount": "400.00",
            "contributed_on": contribution_date.isoformat(),
            "note": "Part payment",
        },
    )
    assert record.status_code == 201, record.text
    record_b = client.post(
        f"/api/v1/contributions/{agreement_b.json()['id']}/records",
        headers=headers,
        json={
            "amount": "500.00",
            "contributed_on": contribution_date.isoformat(),
            "note": "Member B paid",
        },
    )
    assert record_b.status_code == 201, record_b.text
    _logout(client)

    login(client, "contribution-scope-a@example.com")
    agreements = client.get("/api/v1/contributions", headers=headers)
    assert agreements.status_code == 200
    assert [row["id"] for row in agreements.json()] == [agreement_a.json()["id"]]

    own_records = client.get(
        f"/api/v1/contributions/{agreement_a.json()['id']}/records",
        headers=headers,
    )
    assert own_records.status_code == 200
    assert len(own_records.json()) == 1
    assert Decimal(own_records.json()[0]["amount"]) == Decimal("400.00")

    member_payment = client.post(
        f"/api/v1/contributions/{agreement_a.json()['id']}/records",
        headers=headers,
        json={
            "amount": "100.00",
            "contributed_on": date.today().isoformat(),
            "note": "Member-recorded payment",
        },
    )
    assert member_payment.status_code == 201, member_payment.text

    forbidden_payment = client.post(
        f"/api/v1/contributions/{agreement_b.json()['id']}/records",
        headers=headers,
        json={
            "amount": "100.00",
            "contributed_on": date.today().isoformat(),
        },
    )
    assert forbidden_payment.status_code == 404

    other_records = client.get(
        f"/api/v1/contributions/{agreement_b.json()['id']}/records",
        headers=headers,
    )
    assert other_records.status_code == 404

    schedule = client.get("/api/v1/contributions/schedule", headers=headers)
    assert schedule.status_code == 200, schedule.text
    assert schedule.json()
    assert {row["member_id"] for row in schedule.json()} == {member_a["id"]}
    first_due = next(
        row for row in schedule.json()
        if row["due_date"] == start_date.isoformat()
    )
    assert first_due["status"] == "partial"
    assert Decimal(first_due["expected_amount"]) == Decimal("1000.00")
    assert Decimal(first_due["paid_amount"]) == Decimal("500.00")
    assert Decimal(first_due["outstanding_amount"]) == Decimal("500.00")
    _logout(client)

    login(client, "contribution-scope-owner@example.com")
    grant = client.patch(
        f"/api/v1/members/{member_a['id']}",
        headers=headers,
        json={"permissions": {"view_all_contributions": True}},
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["permissions"]["view_all_contributions"] is True
    _logout(client)

    login(client, "contribution-scope-a@example.com")
    authorized_agreements = client.get("/api/v1/contributions", headers=headers)
    assert {row["id"] for row in authorized_agreements.json()} == {
        agreement_a.json()["id"],
        agreement_b.json()["id"],
    }
    authorized_records = client.get(
        f"/api/v1/contributions/{agreement_b.json()['id']}/records",
        headers=headers,
    )
    assert authorized_records.status_code == 200
    assert len(authorized_records.json()) == 1
    forbidden_other_member_record = client.post(
        f"/api/v1/contributions/{agreement_b.json()['id']}/records",
        headers=headers,
        json={
            "amount": "50.00",
            "contributed_on": date.today().isoformat(),
        },
    )
    assert forbidden_other_member_record.status_code == 403
    authorized_schedule = client.get("/api/v1/contributions/schedule", headers=headers)
    assert {row["member_id"] for row in authorized_schedule.json()} == {
        member_a["id"],
        member_b["id"],
    }
    _logout(client)

    login(client, "contribution-scope-b@example.com")
    member_b_agreements = client.get("/api/v1/contributions", headers=headers)
    assert [row["id"] for row in member_b_agreements.json()] == [agreement_b.json()["id"]]
