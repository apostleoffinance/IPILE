
import pytest
from fastapi.testclient import TestClient

from app.services.ai_engine import (
    InventingModel,
    TemplateModel,
    explain,
    flatten_allowed_numbers,
    validate_response,
)
from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_invented_figures_are_rejected() -> None:
    payload = {
        "health": {"score": "80.00", "label": "Healthy"},
        "safe_to_spend": {"current": "150000.00"},
    }
    with pytest.raises(ValueError, match="invented"):
        explain(payload, model=InventingModel())


def test_template_model_only_uses_payload_numbers() -> None:
    payload = {
        "health": {"score": "88.36", "label": "Healthy"},
        "safe_to_spend": {"current": "1490000.00"},
        "wealth": {"net_worth": "3760000.00"},
        "budgets": [],
        "obligations": [],
        "funds": [
            {
                "name": "University fund",
                "current_amount": "150000.00",
                "target_amount": "450000.00",
            }
        ],
    }
    text = explain(payload, model=TemplateModel())
    assert "88.36" in text or "1490000.00" in text or "150000.00" in text
    validate_response(text, payload)
    allowed = flatten_allowed_numbers(payload)
    assert "88.36" in allowed
    assert "150000.00" in allowed


def test_ai_explain_endpoint_server_side(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        seed_household(db)
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert login.status_code == 200
    response = client.post("/api/v1/ai/explain")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "verified_engines"
    assert "explanation" in body
    assert "payload" in body
    assert body["payload"]["health"]["score"]
    # no client key field ever returned
    assert "api_key" not in body
    assert "OPENAI" not in str(body)


def test_ai_requires_auth(client: TestClient) -> None:
    register(client, "ai-auth@example.com")
    client.post("/api/v1/auth/logout")
    response = client.post("/api/v1/ai/explain")
    assert response.status_code == 401
