from app.services.transaction_intelligence import (
    assess_confidence,
    match_alert_account,
    sender_institution_key,
)


def test_sender_domains_resolve_known_bank_aliases() -> None:
    assert sender_institution_key("alerts@gtbank.com") == "gtbank"
    assert sender_institution_key("no-reply@opayweb.com") == "opay"
    assert sender_institution_key("alerts@ubagroup.com") == "uba"


def test_account_match_requires_unique_institution_and_currency() -> None:
    class AccountStub:
        def __init__(self, institution: str, currency: str = "NGN"):
            self.institution = institution
            self.currency = currency

    account, status = match_alert_account(
        [AccountStub("GTBank")], "alerts@gtbank.com", "NGN"
    )
    assert account is not None
    assert status == "exact_institution"

    account, status = match_alert_account(
        [AccountStub("GTBank", "USD")], "alerts@gtbank.com", "NGN"
    )
    assert account is not None
    assert status == "currency_mismatch"

    account, status = match_alert_account(
        [AccountStub("GTBank"), AccountStub("GTBank")], "alerts@gtbank.com", "NGN"
    )
    assert account is None
    assert status == "ambiguous_institution"


def test_confidence_is_explainable_and_never_high_without_currency_or_account() -> None:
    result = assess_confidence(
        sender_verified=True,
        amount_valid=True,
        date_valid=True,
        direction_valid=True,
        currency_explicit=False,
        account_match="currency_unconfirmed",
        category_points=0,
    )
    assert result["band"] == "medium"
    assert result["score"] == 70
    assert any("Currency" in reason for reason in result["reasons"])


def test_high_confidence_requires_verified_sender_and_exact_account() -> None:
    result = assess_confidence(
        sender_verified=True,
        amount_valid=True,
        date_valid=True,
        direction_valid=True,
        currency_explicit=True,
        account_match="exact_institution",
        category_points=5,
    )
    assert result == {"score": 100, "band": "high", "reasons": []}
