from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_me_logout(client: TestClient) -> None:
    payload = {
        "email": "owner@example.com",
        "password": "super-secret-12",
        "display_name": "Partner A",
    }
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201
    assert register.json()["email"] == "owner@example.com"
    assert "ffos_session" in register.cookies
    assert "ffos_csrf" in register.cookies
    set_cookie = register.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Partner A"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    after = client.get("/api/v1/auth/me")
    assert after.status_code == 401


def test_login_rejects_short_password_on_register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "short", "display_name": "A"},
    )
    assert response.status_code == 422


def test_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "super-secret-12",
        "display_name": "Dup",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_csrf_required_on_authenticated_mutation(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "csrf@example.com",
                "password": "super-secret-12",
                "display_name": "Csrf",
            },
        ).status_code
        == 201
    )
    # Raw ASGI call without CSRF header via underlying client
    raw = TestClient(client.app)
    raw.cookies.set("ffos_session", client.cookies["ffos_session"])
    raw.cookies.set("ffos_csrf", client.cookies["ffos_csrf"])
    denied = raw.post("/api/v1/auth/logout")
    assert denied.status_code == 403


def test_password_change(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "pw@example.com",
                "password": "super-secret-12",
                "display_name": "Pw",
            },
        ).status_code
        == 201
    )
    changed = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "super-secret-12", "new_password": "even-more-secret"},
    )
    assert changed.status_code == 204
    client.post("/api/v1/auth/logout")
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "pw@example.com", "password": "super-secret-12"},
    )
    assert bad.status_code == 401
    ok = client.post(
        "/api/v1/auth/login",
        json={"email": "pw@example.com", "password": "even-more-secret"},
    )
    assert ok.status_code == 200
