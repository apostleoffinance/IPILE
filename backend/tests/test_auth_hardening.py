from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.models.session import SessionToken
from tests.conftest import TestingSessionLocal


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


def test_absolute_expired_session_is_rejected(client: TestClient) -> None:
    payload = {
        "email": "absolute-expired@example.com",
        "password": "super-secret-12",
        "display_name": "Absolute Expired",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.cookies["ffos_session"]

    from app.core.security import hash_session_token

    with TestingSessionLocal() as db:
        session = (
            db.query(SessionToken)
            .filter(SessionToken.token_hash == hash_session_token(token))
            .one()
        )
        session.absolute_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_password_change_revokes_other_device_sessions(client: TestClient) -> None:
    payload = {
        "email": "password-revoke@example.com",
        "password": "super-secret-12",
        "display_name": "Password Revoke",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    second = TestClient(client.app)
    assert second.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    ).status_code == 200
    assert second.get("/api/v1/auth/me").status_code == 200

    changed = client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": payload["password"],
            "new_password": "new-secure-password-12",
        },
    )
    assert changed.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 200
    assert second.get("/api/v1/auth/me").status_code == 401


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


def test_readiness_checks_database_and_migrations(client: TestClient) -> None:
    with TestingSessionLocal() as db:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        db.execute(text("DELETE FROM alembic_version"))
        db.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0018_personal_shared_finance')")
        )
        db.commit()

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ipile",
        "database": "connected",
        "migrations": "current",
    }

    live = client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"


def test_readiness_rejects_outdated_migrations(client: TestClient) -> None:
    with TestingSessionLocal() as db:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        db.execute(text("DELETE FROM alembic_version"))
        db.execute(text("INSERT INTO alembic_version (version_num) VALUES ('old_revision')"))
        db.commit()

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert client.head("/").status_code == 503
