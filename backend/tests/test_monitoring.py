from app.core.monitoring import initialize_error_reporting, scrub_error_event


def test_error_event_scrubbing_removes_credentials_and_request_payload() -> None:
    event = {
        "user": {"email": "private@example.com", "id": "123"},
        "request": {
            "url": "https://ipile.example/api/v1/export?token=secret",
            "query_string": "token=secret",
            "data": {"account_number": "1234567890"},
            "cookies": {"ffos_session": "session-secret"},
            "headers": {
                "Cookie": "ffos_session=session-secret",
                "Authorization": "Bearer secret",
                "X-CSRF-Token": "csrf-secret",
                "X-Billing-Secret": "billing-secret",
                "Content-Type": "application/json",
                "X-Request-Id": "request-123",
            },
        },
    }

    cleaned = scrub_error_event(event)

    assert "user" not in cleaned
    request = cleaned["request"]
    assert "data" not in request
    assert "cookies" not in request
    assert "query_string" not in request
    assert request["url"] == "https://ipile.example/api/v1/export"
    assert request["headers"] == {
        "Content-Type": "application/json",
        "X-Request-Id": "request-123",
    }


def test_error_reporting_stays_disabled_without_operator_configured_dsn() -> None:
    assert initialize_error_reporting(dsn="  ", environment="test") is False
