"""Conservative parser for forwarded bank transaction alert emails."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from decimal import Decimal

from app.money import quantize_money
from app.services.import_adapters import ImportRow

_AMOUNT = re.compile(r"(?:NGN|N\s?\$|₦)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_REFERENCE = re.compile(r"(?:reference|ref|session\s?id|transaction\s?id)\s*[:#-]?\s*([A-Z0-9/-]{5,})", re.IGNORECASE)


def parse_bank_alert(*, sender: str, subject: str, body: str) -> ImportRow:
    text = " ".join(part for part in (subject, body) if part)
    amount_match = _AMOUNT.search(text)
    if not amount_match:
        raise ValueError("Could not identify a currency amount in this bank alert.")
    amount = quantize_money(Decimal(amount_match.group(1).replace(",", "")))
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
    else:
        tx_date = date.today()
    reference = _REFERENCE.search(text)
    description = subject.strip() or "Bank alert"
    external_id = reference.group(1) if reference else hashlib.sha256(
        f"{sender}|{subject}|{body}".encode("utf-8")
    ).hexdigest()
    return ImportRow(
        date=tx_date,
        amount=amount,
        type=tx_type,
        description=description[:500],
        external_id=external_id[:200],
        merchant=sender[:200],
    )
