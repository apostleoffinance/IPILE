from types import SimpleNamespace

from fastapi.testclient import TestClient

from tests.conftest import register


def test_daily_automation_cron_requires_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.automation.get_settings",
        lambda: SimpleNamespace(automation_cron_secret="test-cron-secret"),
    )
    response = client.post("/api/v1/automation/cron/daily")
    assert response.status_code == 401


def test_daily_automation_cron_is_household_scoped_and_idempotent(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.api.v1.automation.get_settings",
        lambda: SimpleNamespace(automation_cron_secret="test-cron-secret"),
    )
    register(client, "cron-a@example.com", "Cron A")
    client.post("/api/v1/auth/logout")
    register(client, "cron-b@example.com", "Cron B")

    headers = {"X-Automation-Cron-Secret": "test-cron-secret"}
    first = client.post("/api/v1/automation/cron/daily", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["households"] == 2
    assert first.json()["processed"] == 2
    assert first.json()["failed"] == 0

    second = client.post("/api/v1/automation/cron/daily", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["households"] == 2
    assert second.json()["skipped"] == 2
    assert second.json()["processed"] == 0
