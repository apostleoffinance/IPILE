# IPÌLẸ̀ Connect — inbound bank-alert setup

This runbook configures Postmark Inbound for household bank-alert forwarding. It uses a dedicated subdomain so existing website and mailbox MX records are not changed.

## 1. Choose a domain you control

Choose a dedicated inbound subdomain, for example:

`inbox.<your-owned-domain>`

Do not use the illustrative `ipile.app` or `inbox.ipile.app` values unless that domain is actually registered and controlled by the IPÌLẸ̀ operator.

Set the Render backend environment variables:

- `INBOUND_EMAIL_DOMAIN`: the exact inbound subdomain, e.g. `inbox.<your-owned-domain>`
- `INBOUND_EMAIL_WEBHOOK_SECRET`: a unique random secret (at least 32 random bytes)
- `MAX_IMPORT_UPLOAD_BYTES`: `10485760` for the 10 MiB statement upload limit

Generate the secret in a trusted password manager or local shell. Never commit it, put it in a frontend variable, or paste it into a public issue.

## 2. Configure Postmark Inbound

1. Create or select a Postmark Server.
2. Open its **Inbound Message Stream** and its **Settings**.
3. Configure the inbound domain as the chosen subdomain.
4. Set the inbound webhook URL to:

   `https://ipile:<INBOUND_EMAIL_WEBHOOK_SECRET>@ipile-bmfz.onrender.com/api/v1/imports/inbound-email`

   Replace the placeholder with the same secret configured in Render. The username must be `ipile`. Postmark Inbound supports HTTP Basic Authentication in the webhook URL; IPÌLẸ̀ also retains the `X-Inbound-Email-Secret` option for compatible providers. Postmark does not HMAC-sign inbound webhooks, so keep Basic Auth enabled and consider allowlisting Postmark's published webhook IP ranges at the network edge.
5. Use Postmark's **Check** action to send a test webhook. The endpoint acknowledges accepted, duplicate, and permanently rejected messages with HTTP **200**; rejected messages are recorded in the household review queue and are never posted to the ledger. This prevents unnecessary retries for messages that cannot be parsed safely.

## 3. Add the inbound MX record

At the DNS provider for the chosen subdomain, add only this record:

| Type | Name / Host | Priority | Value | TTL |
|---|---|---:|---|---:|
| MX | `inbox` | 10 | `inbound.postmarkapp.com` | 1800 seconds |

If you choose a different subdomain, use that label in the Name/Host field. Do not replace the root domain's existing MX records; that could interrupt normal business or personal email.

Wait for DNS propagation, then verify the domain in Postmark.

## 4. Verify the application flow

1. Confirm Render has the three environment variables and the latest deployment is Live.
2. Sign in to a disposable IPÌLẸ̀ household and create its bank-alert import address from **Money → Import transactions**.
3. Forward a real or provider-approved test bank alert to that exact address.
4. Confirm the inbound event is accepted (HTTP 200) and appears in the household's review queue.
5. Confirm duplicate delivery of the same Postmark `MessageID` does not create a second review item.
6. Approve the alert against the correct household account and verify the posted amount/date and resulting account balance.
7. Repeat with a second household and confirm the first household's mailbox and pending import are not visible or approvable from the second household.

## 5. Important behavior and limitations

- Inbound bank alerts are **pending review**. They do not change balances until an authorized household owner/partner approves them.
- A bank transaction reference is used for transaction-level deduplication when present; Postmark `MessageID` is used to deduplicate webhook retries.
- Alerts with ambiguous amounts or no usable transaction/provider date are rejected rather than guessed.
- CSV, text statements and selectable-text PDFs are supported. Scanned/image-only PDFs still require OCR and are not supported by this flow.
- The email intake currently parses plain-text bank alerts; it does not automatically ingest PDF attachments from inbound email.
- Do not forward highly sensitive messages unrelated to transaction alerts to a household's import address.
