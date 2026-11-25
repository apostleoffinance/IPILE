# Bank connectivity and reconciliation

## Mono Connect setup

Mono Connect requires a Mono business account that has completed KYB, an app secret key and a webhook configured in the Mono dashboard. IPÌLẸ̀ uses Mono's hosted link URL; it never collects bank passwords. The backend initiates linking at `POST /v2/accounts/initiate`, receives the account ID through `mono.events.account_connected`, waits for `mono.events.account_updated` to report transaction availability, and retrieves transactions from `GET /v2/accounts/{account_id}/transactions`.

Configure these server-only variables:

- `MONO_SECRET_KEY`
- `MONO_WEBHOOK_SECRET`
- `MONO_REDIRECT_URL` (HTTPS)
- `BANK_DATA_ENCRYPTION_KEY` (Fernet URL-safe base64 key)

If any are missing, bank-link and sync endpoints remain disabled. Generate an encryption key with Python's `cryptography.fernet.Fernet.generate_key()`. Keep it in the deployment secret manager; never expose it to frontend builds or logs.

## Workflow and safeguards

1. An owner/partner chooses a shared household account and requests a link.
2. IPÌLẸ̀ generates a random reference and returns the hosted Mono URL.
3. Webhooks are authenticated with the `mono-webhook-secret` header using constant-time comparison. Event IDs are unique; retries are idempotent.
4. Provider account IDs are encrypted at rest. Only institution, currency and last four digits are exposed to the client.
5. Provider balances are stored as provider snapshots, never written over the local account balance.
6. Sync creates reconciliation items, not ledger transactions. CSV/PDF statement preview behaves the same way.
7. Matching requires exact amount, currency and direction within a three-day date window. Suggestions are not automatic confirmations.
8. Owners/partners explicitly confirm a match, post a new transaction, or ignore a row. Transfers cannot be posted as a one-sided transaction.
9. Disconnect revokes the provider link and clears encrypted provider identifiers. Historical reconciliation records remain.

## Statement support

CSV and selectable-text PDF statements are supported through the existing import adapters. Scanned statement PDFs are not OCR'd in this phase. Uploads are size-limited by `MAX_IMPORT_UPLOAD_BYTES`. Opening/closing balance arithmetic is reported where statement rows contain only credits and debits.

## Currency

Mono amounts and balances are supplied in minor units. An explicit currency precision table converts supported currencies (including NGN kobo); unsupported currency precision is rejected instead of guessed.

## Operational notes

Mono availability depends on bank coverage, Mono onboarding and provider uptime. CI uses mocked API responses and does not verify a live bank account. Configure a Mono webhook URL at `/api/v1/webhooks/mono`. Do not run the database migration in production until the deployment owner has scheduled the release and verified backup/rollback procedures.
