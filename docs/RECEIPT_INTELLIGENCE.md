# Receipt intelligence and OCR

## Data flow

1. An owner or partner uploads a JPEG, PNG, WEBP or PDF receipt against a shared household account.
2. The API checks household/account authorization, upload size, media type and file signature.
3. OCR runs in memory. PDF processing is limited to five pages; raster images are limited to 20 megapixels.
4. The API persists only the receipt hash, extracted fields, field-confidence metadata, status and account association. The source image and full OCR text are not persisted.
5. The receipt appears in the review queue. The user can correct merchant, date, amount and currency.
6. Approval creates one expense transaction. Rejection never changes balances.

## Runtime

The backend image installs the Tesseract OCR executable. Python dependencies are declared in
backend/pyproject.toml (pytesseract, Pillow and PyMuPDF). The OCR engine is local; no external
OCR vendor or API credential is required.

If Tesseract is unavailable, the upload endpoint returns HTTP 503. It does not silently mark a
receipt as successfully processed.

## Safety

- Files are size-limited and processed in memory.
- PDF page count and image pixel dimensions are bounded.
- MIME type and file signatures are checked before OCR.
- Only owner/partner roles may upload, correct, approve or reject receipts.
- Only shared household accounts are eligible for receipt posting.
- The receipt currency must match the destination account currency.
- OCR output is untrusted and cannot mutate the ledger until explicit approval.
- Duplicate detection is scoped to the household and uses a SHA-256 content fingerprint.
- Approval is row-locked and the resulting transaction has a deterministic receipt external ID.
- The original receipt image is not retained; households should retain their own source documents.
