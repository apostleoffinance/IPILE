from io import BytesIO

import pytest
from PIL import Image

from app.services import receipt_ocr


def test_receipt_parser_prefers_grand_total_and_detects_date() -> None:
    extracted = receipt_ocr._extract_fields(
        "FRESH MART\nDate: 2026-11-20\nSubtotal NGN 4,000.00\n"
        "Total NGN 4,300.00\nGrand Total NGN 4,500.00",
        0.92,
    )
    assert extracted["merchant"] == "FRESH MART"
    assert extracted["date"] == "2026-11-20"
    assert extracted["amount"] == "4500.00"
    assert extracted["currency"] == "NGN"
    assert extracted["field_confidence"]["amount"] == 0.92


def test_receipt_parser_does_not_guess_between_same_priority_totals() -> None:
    extracted = receipt_ocr._extract_fields(
        "SHOP\nDate: 2026-11-20\nGrand Total NGN 4,500.00\nGrand Total NGN 4,700.00",
        0.9,
    )
    assert extracted["amount"] is None
    assert any("Multiple plausible totals" in warning for warning in extracted["warnings"])


def test_receipt_parser_does_not_invent_missing_date_or_amount() -> None:
    extracted = receipt_ocr._extract_fields("CORNER STORE\nThank you", 0.8)
    assert extracted["merchant"] == "CORNER STORE"
    assert extracted["date"] is None
    assert extracted["amount"] is None


def test_extract_receipt_uses_ocr_adapter_and_returns_confidence(monkeypatch) -> None:
    image = Image.new("RGB", (100, 100), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    monkeypatch.setattr(
        receipt_ocr,
        "_ocr_image",
        lambda _: ("FRESH MART\nDate: 2026-11-20\nGrand Total NGN 4500.00", 0.91),
    )
    result = receipt_ocr.extract_receipt(output.getvalue(), "image/png")
    assert result["merchant"] == "FRESH MART"
    assert result["date"] == "2026-11-20"
    assert result["amount"] == "4500.00"
    assert result["overall_confidence"] == 0.91


def test_receipt_ocr_rejects_unsupported_media_type() -> None:
    with pytest.raises(ValueError, match="JPEG, PNG"):
        receipt_ocr.extract_receipt(b"not an image", "text/plain")


def test_receipt_ocr_rejects_oversized_image_dimensions(monkeypatch) -> None:
    image = Image.new("RGB", (100, 100), "white")
    monkeypatch.setattr(receipt_ocr, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="dimensions"):
        receipt_ocr._images_from_upload(image_to_png(image), "image/png")


def image_to_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
