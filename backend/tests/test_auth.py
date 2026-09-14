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
