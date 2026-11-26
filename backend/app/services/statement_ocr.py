"""Private, bounded OCR for scanned bank statement PDFs and images."""

from __future__ import annotations

import gc
import re
from io import BytesIO

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageOps

from app.services.import_adapters import ImportRow, _make_row, _parse_amount

MAX_OCR_PAGES = 12
MAX_IMAGE_PIXELS = 16_000_000
OCR_DPI_SCALE = 1.8
OCR_PAGE_TIMEOUT_SECONDS = 12
DATE_PATTERN = re.compile(
    r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b"
)
NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:₦|NGN\s*)?\(?-?\d[\d,]*\.\d{2}\)?(?:\s*(?:CR|DR))?",
    re.I,
)


def _ocr_image(image: Image.Image) -> str:
    if image.width < 1 or image.height < 1 or image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("This statement image is too large to process safely.")
    grayscale = ImageOps.grayscale(image)
    try:
        prepared = ImageOps.autocontrast(grayscale)
        try:
            return pytesseract.image_to_string(
                prepared,
                config="--psm 6",
                timeout=OCR_PAGE_TIMEOUT_SECONDS,
            )
        except RuntimeError as exc:
            raise ValueError(
                "Scanning took too long on one page. Try a clearer or smaller PDF."
            ) from exc
        finally:
            prepared.close()
    finally:
        grayscale.close()


def extract_pdf_ocr_text(content: bytes) -> str:
    try:
        document = pdfium.PdfDocument(content)
    except Exception as exc:
        raise ValueError("This PDF could not be opened. Please upload a valid PDF.") from exc
    if len(document) > MAX_OCR_PAGES:
        document.close()
        raise ValueError(f"Scanned statements are limited to {MAX_OCR_PAGES} pages per upload.")
    pages: list[str] = []
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = None
            image = None
            try:
                width, height = page.get_size()
                if width * height * OCR_DPI_SCALE * OCR_DPI_SCALE > MAX_IMAGE_PIXELS:
                    raise ValueError("A scanned PDF page is too large to process safely.")
                bitmap = page.render(scale=OCR_DPI_SCALE)
                image = bitmap.to_pil()
                pages.append(_ocr_image(image))
            finally:
                if image is not None:
                    image.close()
                if bitmap is not None:
                    bitmap.close()
                page.close()
                # Release native PDF and image allocations between pages on small instances.
                gc.collect()
    finally:
        document.close()
    return "\n".join(pages).strip()


def extract_image_ocr_text(content: bytes) -> str:
    prepared = None
    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            prepared = ImageOps.exif_transpose(image)
            return _ocr_image(prepared)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "This image could not be opened. Please upload a clear PNG, JPEG or WebP."
        ) from exc
    finally:
        if prepared is not None:
            prepared.close()


def parse_ocr_statement(text: str) -> list[ImportRow]:
    """Conservative line parser: rows without a clear date and amount are never guessed."""
    rows: list[ImportRow] = []
    rejected = 0
    upper_text = text.upper()
    currency = (
        "NGN" if "₦" in text or "NGN" in upper_text
        else "USD" if "USD" in upper_text or "US$" in upper_text
        else "EUR" if "€" in text or "EUR" in upper_text
        else "GBP" if "£" in text or "GBP" in upper_text
        else None
    )
    for index, line in enumerate(text.splitlines(), start=1):
        match = DATE_PATTERN.match(line)
        if not match:
            continue
        raw_date = match.group(1)
        remainder = line[match.end():]
        values = list(NUMBER_PATTERN.finditer(remainder))
        if not values:
            rejected += 1
            continue
        tokens = [item.group(0).strip() for item in values]
        marker = remainder.upper()
        description = remainder[:values[0].start()].strip(" |:-")
        try:
            if len(tokens) >= 3:
                debit = _parse_amount(tokens[-3].replace("CR", "").replace("DR", ""))
                credit = _parse_amount(tokens[-2].replace("CR", "").replace("DR", ""))
                if debit and credit:
                    raise ValueError("Both debit and credit columns appear populated.")
                if debit:
                    amount, tx_type = -abs(debit), "expense"
                elif credit:
                    amount, tx_type = abs(credit), "income"
                else:
                    amount = _parse_amount(tokens[-3])
                    tx_type = "income" if " CR" in marker else "expense"
            else:
                token = tokens[0]
                amount = _parse_amount(token.replace("CR", "").replace("DR", ""))
                if "DR" in token.upper() or " DR" in marker or amount < 0:
                    amount, tx_type = -abs(amount), "expense"
                elif "CR" in token.upper() or " CR" in marker:
                    amount, tx_type = abs(amount), "income"
                else:
                    # Without debit/credit context, do not infer direction from an OCR guess.
                    rejected += 1
                    continue
            if not description:
                description = "Statement transaction"
            rows.append(
                _make_row(
                    raw_date=raw_date,
                    amount=amount,
                    tx_type=tx_type,
                    description=description,
                    external_id=None,
                    merchant=description,
                    row_index=index,
                    currency=currency,
                )
            )
        except ValueError:
            rejected += 1
    if not rows:
        raise ValueError(
            "We could not confidently identify transaction rows in this scanned statement. "
            "Try a clearer scan or upload the bank's CSV export."
        )
    # OCR can produce partial lines; expose only valid rows and require the user to review them.
    return rows
