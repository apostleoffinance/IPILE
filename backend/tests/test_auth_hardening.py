from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.session import SessionToken


def test_independent_devices_keep_independent_sessions(client: TestClient) -> None:
    payload = {
        "email": "multi-device@example.com",
        "password": "super-secret-12",
        "display_name": "Multi Device",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = TestClient(client.app)
    login = second.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert second.get("/api/v1/auth/me").status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert second.get("/api/v1/auth/me").status_code == 200


def test_idle_expired_session_is_rejected(client: TestClient) -> None:
    payload = {
        "email": "expired-session@example.com",
        "password": "super-secret-12",
        "display_name": "Expired Session",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.cookies["ffos_session"]

    with TestingSessionLocal() as db:
        from app.core.security import hash_session_token

        session = (
            db.query(SessionToken)
            .filter(SessionToken.token_hash == hash_session_token(token))
            .one()
        )
        session.idle_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_rejects_missing_and_mismatched_tokens(client: TestClient) -> None:
    payload = {
        "email": "csrf-hardening@example.com",
        "password": "super-secret-12",
        "display_name": "CSRF",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    raw = TestClient(client.app)
    raw.cookies.set("ffos_session", client.cookies["ffos_session"])
    raw.cookies.set("ffos_csrf", client.cookies["ffos_csrf"])

    assert raw.post("/api/v1/auth/password/change", json={
        "current_password": payload["password"],
        "new_password": "another-secure-12",
    }).status_code == 403

    mismatch = raw.post(
        "/api/v1/auth/password/change",
        headers={"X-CSRF-Token": "not-the-cookie-token"},
        json={
            "current_password": payload["password"],
            "new_password": "another-secure-12",
        },
    )
    assert mismatch.status_code == 403


def test_readiness_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ipile",
        "database": "connected",
    }

    live = client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
