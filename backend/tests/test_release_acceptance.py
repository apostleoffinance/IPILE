from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def _create_financial_fixture(client: TestClient, *, label: str, amount: str) -> tuple[str, str]:
    account = client.post(
        "/api/v1/accounts",
        json={"name": f"{label} account", "type": "bank", "current_balance": amount},
    )
    assert account.status_code == 201, account.text
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account.json()["id"],
            "amount": "1250.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "description": f"{label} private transaction",
        },
    )
    assert transaction.status_code == 201, transaction.text
    return account.json()["id"], transaction.json()["id"]


def test_release_acceptance_two_households_are_isolated_end_to_end(client: TestClient) -> None:
    # Household A creates financial data and a support request.
    register(client, "release-a@example.com", "Release Household A")
    household_a = client.get("/api/v1/households/current").json()
    account_a, transaction_a = _create_financial_fixture(
        client, label="Household A", amount="100000.00"
    )
    ticket_a = client.post(
        "/api/v1/support/tickets",
        json={"subject": "A private support request", "body": "Household A details."},
    )
    assert ticket_a.status_code == 201, ticket_a.text
    ticket_a_id = ticket_a.json()["id"]
    export_a = client.get("/api/v1/export")
    assert export_a.status_code == 200, export_a.text
    assert any(row["id"] == account_a for row in export_a.json()["accounts"])
    assert any(row["id"] == transaction_a for row in export_a.json()["transactions"])
    _logout(client)

    # Household B creates its own data. A's identifiers and household header
    # must not reveal or mutate A's records.
    register(client, "release-b@example.com", "Release Household B")
    household_b = client.get("/api/v1/households/current").json()
    assert household_a["id"] != household_b["id"]
    account_b, transaction_b = _create_financial_fixture(
        client, label="Household B", amount="200000.00"
    )

    assert client.get("/api/v1/accounts").status_code == 200
    visible_accounts = client.get("/api/v1/accounts").json()
    assert {row["id"] for row in visible_accounts} == {account_b}
    assert client.get(f"/api/v1/accounts/{account_a}").status_code == 404
    assert client.get(f"/api/v1/transactions/{transaction_a}").status_code == 404
    assert client.get(
        "/api/v1/accounts", headers={"X-Household-Id": household_a["id"]}
    ).status_code == 403

    export_b = client.get("/api/v1/export")
    assert export_b.status_code == 200, export_b.text
    assert {row["id"] for row in export_b.json()["accounts"]} == {account_b}
    assert {row["id"] for row in export_b.json()["transactions"]} == {transaction_b}
    assert all(
        row["description"] != "Household A private transaction"
        for row in export_b.json()["transactions"]
    )

    # Support requests are user-scoped; one household's ticket is not exposed
    # to a different household owner.
    assert client.get("/api/v1/support/tickets").json() == []
    ticket_b = client.post(
        "/api/v1/support/tickets",
        json={"subject": "B private support request", "body": "Household B details."},
    )
    assert ticket_b.status_code == 201, ticket_b.text
    visible_tickets = client.get("/api/v1/support/tickets").json()
    assert len(visible_tickets) == 1
    assert visible_tickets[0]["id"] != ticket_a_id

    # Verify the reverse direction as well: A cannot access B's data.
    _logout(client)
    login(client, "release-a@example.com")
    assert client.get(f"/api/v1/accounts/{account_b}").status_code == 404
    assert client.get(f"/api/v1/transactions/{transaction_b}").status_code == 404
    assert client.get(
        "/api/v1/accounts", headers={"X-Household-Id": household_b["id"]}
    ).status_code == 403
    export_a_again = client.get("/api/v1/export")
    assert export_a_again.status_code == 200, export_a_again.text
    assert {row["id"] for row in export_a_again.json()["accounts"]} == {account_a}
    assert {row["id"] for row in export_a_again.json()["transactions"]} == {
        transaction_a
    }
    assert [row["id"] for row in client.get("/api/v1/support/tickets").json()] == [
        ticket_a_id
    ]


def test_release_acceptance_health_readiness_requires_current_database_schema(
    client: TestClient,
) -> None:
    from sqlalchemy import text

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        db.execute(text("DELETE FROM alembic_version"))
        db.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0016_import_mailboxes')"
            )
        )
        db.commit()

    ready = client.get("/api/v1/health")
    assert ready.status_code == 200, ready.text
    assert ready.json()["database"] == "connected"
    assert ready.json()["migrations"] == "current"
    assert ready.headers.get("X-Request-Id")

    with TestingSessionLocal() as db:
        db.execute(text("DELETE FROM alembic_version"))
        db.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('outdated_migration')"
            )
        )
        db.commit()

    stale = client.get("/api/v1/health")
    assert stale.status_code == 503
