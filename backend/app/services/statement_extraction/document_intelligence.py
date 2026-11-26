"""Document capability detection independent of bank identity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

import pdfplumber


class PDFContentKind(StrEnum):
    TEXT = "text"
    MIXED = "mixed"
    SCANNED = "scanned"
    EMPTY = "empty"


@dataclass(frozen=True, slots=True)
class PDFPageProfile:
    page_number: int
    character_count: int
    word_count: int
    table_count: int
    has_selectable_text: bool
    has_images: bool


@dataclass(frozen=True, slots=True)
class PDFDocumentProfile:
    page_count: int
    pages: tuple[PDFPageProfile, ...]
    content_kind: PDFContentKind
    has_selectable_text: bool
    has_tables: bool
    scanned_page_numbers: tuple[int, ...]


def inspect_pdf_document(content: bytes) -> PDFDocumentProfile:
    """Inspect PDF text, tables and image presence without rendering pages."""
    try:
        document = pdfplumber.open(BytesIO(content))
    except Exception as exc:
        raise ValueError("This PDF could not be opened. Please upload a valid PDF.") from exc

    pages: list[PDFPageProfile] = []
    try:
        for page_number, page in enumerate(document.pages, start=1):
            text = page.extract_text() or ""
            words = page.extract_words() or []
            tables = page.find_tables()
            images = bool(page.images)
            pages.append(PDFPageProfile(
                page_number=page_number,
                character_count=len(text.strip()),
                word_count=len(words),
                table_count=len(tables),
                has_selectable_text=bool(text.strip()),
                has_images=images,
            ))
    finally:
        document.close()

    if not pages or not any(page.character_count or page.has_images for page in pages):
        kind = PDFContentKind.EMPTY
    elif all(not page.has_selectable_text for page in pages):
        kind = PDFContentKind.SCANNED
    elif any(not page.has_selectable_text for page in pages):
        kind = PDFContentKind.MIXED
    else:
        kind = PDFContentKind.TEXT

    return PDFDocumentProfile(
        page_count=len(pages),
        pages=tuple(pages),
        content_kind=kind,
        has_selectable_text=any(page.has_selectable_text for page in pages),
        has_tables=any(page.table_count for page in pages),
        scanned_page_numbers=tuple(
            page.page_number for page in pages if not page.has_selectable_text
        ),
    )
