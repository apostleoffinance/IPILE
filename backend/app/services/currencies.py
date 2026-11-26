"""Currency metadata and auditable FX conversion services."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.currency import ExchangeRate
from app.models.household import Household

SUPPORTED_CURRENCIES = {
    "AED": ("UAE Dirham", "د.إ"), "AUD": ("Australian Dollar", "A$"),
    "BRL": ("Brazilian Real", "R$"), "CZK": ("Czech Koruna", "Kč"),
    "DKK": ("Danish Krone", "kr"), "HKD": ("Hong Kong Dollar", "HK$"),
    "HUF": ("Hungarian Forint", "Ft"), "IDR": ("Indonesian Rupiah", "Rp"),
    "ILS": ("Israeli New Shekel", "₪"), "ISK": ("Icelandic Króna", "kr"),
    "MXN": ("Mexican Peso", "MX$"), "MYR": ("Malaysian Ringgit", "RM"),
    "CAD": ("Canadian Dollar", "C$"), "CHF": ("Swiss Franc", "CHF"),
    "CNY": ("Chinese Yuan", "¥"), "EUR": ("Euro", "€"),
    "GBP": ("British Pound", "£"), "GHS": ("Ghanaian Cedi", "₵"),
    "INR": ("Indian Rupee", "₹"), "JPY": ("Japanese Yen", "¥"),
    "KES": ("Kenyan Shilling", "KSh"), "NGN": ("Nigerian Naira", "₦"),
    "NOK": ("Norwegian Krone", "kr"), "NZD": ("New Zealand Dollar", "NZ$"),
    "PHP": ("Philippine Peso", "₱"), "PLN": ("Polish Złoty", "zł"),
    "RON": ("Romanian Leu", "lei"), "RWF": ("Rwandan Franc", "RF"),
    "SEK": ("Swedish Krona", "kr"), "THB": ("Thai Baht", "฿"),
    "TRY": ("Turkish Lira", "₺"), "TWD": ("New Taiwan Dollar", "NT$"),
    "UAH": ("Ukrainian Hryvnia", "₴"), "VND": ("Vietnamese Đồng", "₫"),
    "SAR": ("Saudi Riyal", "﷼"), "SGD": ("Singapore Dollar", "S$"),
    "USD": ("US Dollar", "$"), "ZAR": ("South African Rand", "R"),
}
CENT = Decimal("0.01")


class CurrencyError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=422, detail=message)


def validate_currency(code: str) -> str:
    normalized = code.upper().strip()
    if normalized not in SUPPORTED_CURRENCIES:
        raise CurrencyError(f"Unsupported currency code: {code}")
    return normalized


def currency_catalog() -> list[dict[str, str]]:
    return [
        {"code": code, "name": name, "symbol": symbol}
        for code, (name, symbol) in sorted(SUPPORTED_CURRENCIES.items())
    ]


def _stored_rate(db: Session, household_id, base: str, quote: str, on_date: date):
    row = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.household_id == household_id,
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
            ExchangeRate.rate_date <= on_date,
        )
        .order_by(ExchangeRate.rate_date.desc(), ExchangeRate.fetched_at.desc())
        .first()
    )
    if row:
        return row.rate, row.rate_date, row.source
    inverse = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.household_id == household_id,
            ExchangeRate.base_currency == quote,
            ExchangeRate.quote_currency == base,
            ExchangeRate.rate_date <= on_date,
        )
        .order_by(ExchangeRate.rate_date.desc(), ExchangeRate.fetched_at.desc())
        .first()
    )
    if inverse:
        return Decimal("1") / Decimal(inverse.rate), inverse.rate_date, inverse.source + ":inverse"
    return None


def get_rate(db: Session, household_id, base: str, quote: str, on_date: date):
    base, quote = validate_currency(base), validate_currency(quote)
    if base == quote:
        return Decimal("1"), on_date, "identity"
    stored = _stored_rate(db, household_id, base, quote, on_date)
    if stored and (on_date - stored[1]).days <= 4:
        return stored
    # Frankfurter publishes reference rates from central-bank data. Fetch the
    # requested historical date; never substitute today's rate for a past date.
    rate_source = "frankfurter"
    try:
        response = httpx.get(
            f"https://api.frankfurter.dev/v1/{on_date.isoformat()}",
            params={"base": base, "symbols": quote},
            timeout=8.0,
        )
        response.raise_for_status()
        payload = response.json()
        rate = Decimal(str(payload["rates"][quote]))
        actual_date = date.fromisoformat(payload["date"])
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as primary_exc:
        # Frankfurter is the preferred historical reference source. It does not
        # publish every world currency, so use open.er-api for current rates
        # only; never substitute a current rate for a historical transaction.
        household = db.get(Household, household_id) if household_id else None
        local_today = (
            datetime.now(ZoneInfo(household.timezone)).date()
            if household is not None
            else date.today()
        )
        if on_date != local_today:
            raise CurrencyError(
                "No verified historical "
                f"{base}/{quote} exchange rate is available for {on_date.isoformat()}."
            ) from primary_exc
        try:
            response = httpx.get(f"https://open.er-api.com/v6/latest/{base}", timeout=8.0)
            response.raise_for_status()
            payload = response.json()
            if payload.get("result") != "success":
                raise ValueError("FX provider did not return success.")
            rate = Decimal(str(payload["rates"][quote]))
            updated_at = datetime.fromtimestamp(
                int(payload["time_last_update_unix"]), tz=UTC
            )
            actual_date = updated_at.date()
            rate_source = "open-er-api"
            if (on_date - actual_date).days > 4:
                raise ValueError("FX provider rate is too stale.")
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as fallback_exc:
            raise CurrencyError(
                f"No verified {base}/{quote} exchange rate is available for {on_date.isoformat()}."
            ) from fallback_exc
    if rate <= 0:
        raise CurrencyError("Exchange-rate provider returned a non-positive rate.")
    row = ExchangeRate(
        household_id=household_id, base_currency=base, quote_currency=quote,
        rate=rate, rate_date=actual_date, source=rate_source,
    )
    db.add(row)
    db.flush()
    return rate, actual_date, rate_source


def convert_amount(
    db: Session,
    household_id,
    amount: Decimal,
    base: str,
    quote: str,
    on_date: date,
):
    rate, rate_date, source = get_rate(db, household_id, base, quote, on_date)
    converted = (Decimal(amount) * rate).quantize(CENT, rounding=ROUND_HALF_EVEN)
    return {
        "amount": format(converted, ".2f"),
        "original_amount": format(Decimal(amount), ".2f"),
        "from_currency": base,
        "to_currency": quote,
        "rate": format(rate, ".12f"),
        "rate_date": rate_date,
        "source": source,
    }


def amount_in_base_currency(
    db: Session, household, amount: Decimal, currency: str, on_date: date
) -> Decimal:
    """Convert a native amount into the household ledger currency without floats."""
    base = validate_currency(household.base_currency)
    source = validate_currency(currency)
    if source == base:
        return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_EVEN)
    result = convert_amount(db, household.id, Decimal(amount), source, base, on_date)
    return Decimal(result["amount"])


def transaction_amount_in_base(transaction, base_currency: str) -> Decimal:
    """Read the persisted transaction conversion; refuse ambiguous legacy FX rows."""
    if transaction.base_amount is not None:
        if transaction.base_currency != base_currency:
            raise CurrencyError(
                "Transaction reporting currency does not match the household ledger currency."
            )
        return Decimal(transaction.base_amount)
    if transaction.currency == base_currency:
        return Decimal(transaction.amount)
    raise CurrencyError(
        f"Transaction {transaction.id} has no historical base-currency amount; "
        "reconcile its FX rate before using it in totals."
    )
