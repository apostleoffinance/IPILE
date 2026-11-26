"""Conservative parser for forwarded bank transaction alert emails."""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from email.utils import parsedate_to_datetime

from app.money import quantize_money
from app.services.import_adapters import ImportRow

_CURRENCY_CODES = (
    "AED|AUD|BRL|CAD|CHF|CNY|CZK|DKK|EUR|GBP|GHS|HKD|HUF|IDR|ILS|INR|ISK|JPY|KES|KRW|"
    "MXN|MYR|NOK|NZD|PHP|PLN|RON|RWF|SAR|SEK|SGD|THB|TRY|TWD|UAH|USD|VND|ZAR|NGN"
)
_AMOUNT = re.compile(
    rf"(?:(?P<code>\b(?:{_CURRENCY_CODES})\b)\s*|"
    r"(?P<symbol>₦|£|€|₹|₵|د.إ|R\$)\s*|(?P<dollar>\$)\s*)"
    r"(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_SYMBOL_CURRENCIES = {"₦": "NGN", "£": "GBP", "€": "EUR", "₹": "INR", "₵": "GHS", "R$": "BRL"}
_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_REFERENCE = re.compile(
    r"(?:reference|ref|session\s?id|transaction\s?id)\s*[:#-]?\s*([A-Z0-9/-]{5,})",
    re.IGNORECASE,
)


def _sender_domain(sender: str) -> str:
    address = sender.strip().lower()
    if "<" in address and ">" in address:
        address = address.rsplit("<", 1)[-1].split(">", 1)[0]
    return address.rsplit("@", 1)[-1].strip()


def parse_bank_alert(
    *,
    sender: str,
    subject: str,
    body: str,
    email_date: str | None = None,
    message_id: str | None = None,
) -> ImportRow:
    """Extract one unambiguous NGN transaction.

    Provider Message-IDs are delivery identifiers, not bank transaction
    identifiers. The fallback fingerprint deliberately excludes Message-ID so
    re-forwarding the same alert does not create a second ledger transaction.
    """
    text = " ".join(part for part in (subject, body) if part)
    amount_matches = list(_AMOUNT.finditer(text))
    if len(amount_matches) != 1:
        raise ValueError("Bank alert must contain exactly one unambiguous currency amount.")
    amount_match = amount_matches[0]
    amount = quantize_money(Decimal(amount_match.group("amount").replace(",", "")))
    currency_code = (amount_match.group("code") or "").upper() or None
    if not currency_code and amount_match.group("symbol"):
        currency_code = _SYMBOL_CURRENCIES.get(amount_match.group("symbol"))
    # "$" is deliberately unresolved: it is used by several currencies.
    if amount <= 0:
        raise ValueError("Bank alert transaction amount must be greater than zero.")

    lowered = text.lower()
    if any(
        word in lowered
        for word in ("credit alert", "credited", "deposit received", "transfer received")
    ):
        tx_type = "income"
    elif any(
        word in lowered
        for word in ("debit alert", "debited", "purchase", "withdrawal", "transfer to")
    ):
        tx_type = "expense"
    else:
        raise ValueError("Could not determine whether this alert is a debit or credit.")

    date_match = _DATE.search(text)
    if date_match:
        raw_date = date_match.group(1)
        from app.services.import_adapters import _parse_date

        tx_date = _parse_date(raw_date)
    elif email_date:
        try:
            tx_date = parsedate_to_datetime(email_date).date()
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Bank alert date is missing or invalid.") from exc
    else:
        raise ValueError("Bank alert has no transaction date or valid provider message date.")

    reference = _REFERENCE.search(text)
    description = subject.strip() or "Bank alert"
    if reference:
        # Bank references are the strongest cross-delivery identity.
        external_id = f"bankref:{_sender_domain(sender)}:{reference.group(1).upper()}"
    else:
        # Normalize whitespace/case and ignore provider Message-ID. This is a
        # conservative fallback: uncertain content is still held for review.
        normalized = " ".join(text.lower().split())
        fingerprint = "|".join(
            (_sender_domain(sender), tx_date.isoformat(), tx_type, str(amount), normalized)
        )
        external_id = "alert:" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    return ImportRow(
        date=tx_date,
        amount=amount,
        type=tx_type,
        description=description[:500],
        external_id=external_id[:200],
        merchant=_sender_domain(sender)[:200],
        currency=currency_code,
    )
