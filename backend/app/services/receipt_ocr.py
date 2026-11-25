"""Privacy-conscious receipt OCR. Source files are processed in memory and never stored."""
from __future__ import annotations

import re
import shutil
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

MAX_PDF_PAGES = 5
MAX_IMAGE_PIXELS = 20_000_000
MAX_PDF_PAGE_PIXELS = 4_000_000
CURRENCY_CODES = {
    "NGN": "NGN", "₦": "NGN", "USD": "USD", "$": "USD",
    "GBP": "GBP", "£": "GBP", "EUR": "EUR", "€": "EUR",
}


def _normalise_amount(raw: str) -> Decimal:
    cleaned = re.sub(r"[^0-9.,()-]", "", raw).replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Receipt total is not a valid amount.") from exc
    if value <= 0 or value > Decimal("9999999999999999.99"):
        raise ValueError("Receipt total is outside the supported range.")
    return value.quantize(Decimal("0.01"))


def _ocr_image(image: Image.Image) -> tuple[str, float]:
    if not shutil.which("tesseract"):
        raise RuntimeError("Receipt OCR is not available on this server.")
    if image.width < 1 or image.height < 1 or image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("Receipt image dimensions exceed the processing limit.")
    image.load()
    prepared = ImageOps.autocontrast(ImageOps.grayscale(image))
    data = pytesseract.image_to_data(prepared, output_type=Output.DICT, config="--psm 6")
    scores = [
        float(score) for score, word in zip(data["conf"], data["text"], strict=False)
        if word and word.strip() and str(score).replace(".", "", 1).isdigit() and float(score) >= 0
    ]
    text = pytesseract.image_to_string(prepared, config="--psm 6")
    return text, (sum(scores) / len(scores) / 100 if scores else 0.0)


def _images_from_upload(content: bytes, media_type: str) -> list[Image.Image]:
    if media_type == "application/pdf":
        try:
            document = pdfium.PdfDocument(content)
        except Exception as exc:
            raise ValueError("The uploaded PDF is invalid or unreadable.") from exc
        try:
            if len(document) < 1 or len(document) > MAX_PDF_PAGES:
                raise ValueError(
                    f"Receipt PDF must contain between 1 and {MAX_PDF_PAGES} pages."
                )
            images = []
            for index in range(len(document)):
                page = document[index]
                try:
                    width, height = page.get_size()
                    if width * height * 4 > MAX_PDF_PAGE_PIXELS:
                        raise ValueError(
                            "Receipt PDF page dimensions exceed the processing limit."
                        )
                    bitmap = page.render(scale=2)
                    try:
                        images.append(bitmap.to_pil().convert("RGB"))
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            return images
        finally:
            document.close()
    try:
        image = Image.open(BytesIO(content))
        if image.width < 1 or image.height < 1 or image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("Receipt image dimensions exceed the processing limit.")
        image.verify()
        image = Image.open(BytesIO(content)).convert("RGB")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("The uploaded image is invalid or unreadable.") from exc
    return [image]


def _extract_fields(text: str, confidence: float) -> dict:
    normalised = re.sub(r"\s+", " ", text).strip()
    currency_pattern = r"(NGN|₦|USD|GBP|EUR|[$£€])"
    amount_pattern = r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+\.[0-9]{2})"
    label_pattern = (
        r"\b(grand\s+total|amount\s+due|total\s+amount|net\s+amount|total)\b"
        rf"\s*[:\-]?\s*{currency_pattern}?\s*{amount_pattern}"
    )
    labelled = re.findall(label_pattern, normalised, flags=re.IGNORECASE)
    amount = None
    currency = None
    warnings = []
    if labelled:
        priority = {
            "grand total": 0,
            "amount due": 1,
            "total amount": 2,
            "net amount": 3,
            "total": 4,
        }
        best_priority = min(priority.get(item[0].lower(), 9) for item in labelled)
        best = [item for item in labelled if priority.get(item[0].lower(), 9) == best_priority]
        if len(best) == 1:
            _, symbol, raw_amount = best[0]
            try:
                amount = str(_normalise_amount(raw_amount))
                currency = CURRENCY_CODES.get(symbol.upper(), CURRENCY_CODES.get(symbol))
            except ValueError:
                warnings.append("The detected total could not be normalised.")
        else:
            warnings.append("Multiple plausible totals were detected; confirm the amount manually.")
    else:
        coded = re.findall(
            rf"{currency_pattern}\s*{amount_pattern}", normalised, flags=re.IGNORECASE
        )
        if len(coded) == 1:
            symbol, raw_amount = coded[0]
            try:
                amount = str(_normalise_amount(raw_amount))
                currency = CURRENCY_CODES.get(symbol.upper(), CURRENCY_CODES.get(symbol))
            except ValueError:
                warnings.append("The detected total could not be normalised.")
        elif len(coded) > 1:
            warnings.append("Multiple plausible totals were detected; confirm the amount manually.")
        else:
            warnings.append("No unambiguous currency total was detected.")

    date_match = re.search(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        normalised,
    )
    receipt_date = None
    if date_match:
        from datetime import datetime
        raw_date = date_match.group(1)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y"):
            try:
                receipt_date = datetime.strptime(raw_date, fmt).date().isoformat()
                break
            except ValueError:
                continue
    if not receipt_date:
        warnings.append("No supported receipt date was detected.")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    merchant = next(
        (
            line[:200] for line in lines[:5]
            if re.search(r"[A-Za-z]{3}", line)
            and not re.search(r"receipt|invoice|tax\s+invoice|www\.", line, re.I)
        ),
        None,
    )
    if not merchant:
        warnings.append("Merchant could not be identified confidently.")

    field_confidence = {
        "merchant": round(confidence, 3) if merchant else 0.0,
        "date": round(confidence, 3) if receipt_date else 0.0,
        "amount": round(confidence, 3) if amount else 0.0,
    }
    return {
        "merchant": merchant,
        "date": receipt_date,
        "amount": amount,
        "currency": currency,
        "field_confidence": field_confidence,
        "overall_confidence": round(confidence, 3),
        "warnings": warnings,
    }


def extract_receipt(content: bytes, media_type: str) -> dict:
    if media_type not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        raise ValueError("Upload a JPEG, PNG, WEBP image or PDF receipt.")
    images = _images_from_upload(content, media_type)
    page_texts = []
    page_confidences = []
    for image in images:
        page_text, page_confidence = _ocr_image(image)
        page_texts.append(page_text)
        page_confidences.append(page_confidence)
    text = "\n".join(page_texts)
    if not text.strip():
        raise ValueError("No readable text was found. Retake the photo with better lighting.")
    confidence = sum(page_confidences) / len(page_confidences)
    return _extract_fields(text, confidence)
