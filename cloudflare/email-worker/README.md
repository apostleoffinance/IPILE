# IPÌLẸ̀ inbound bank-alert Email Worker

This Worker is intentionally separate from the public Next.js Worker. It receives mail through Cloudflare Email Routing, validates the envelope recipient and configured bank sender domains, checks Cloudflare-provided Authentication-Results, parses MIME safely, and sends a normalized payload to the existing FastAPI inbound endpoint over HTTPS.

## Required Worker secrets

Set with Wrangler (never commit values):

```sh
npx wrangler secret put INBOUND_WEBHOOK_SECRET
npx wrangler secret put ALLOWED_BANK_SENDER_DOMAINS
```

`ALLOWED_BANK_SENDER_DOMAINS` is a comma-separated allowlist, for example bank-owned domains confirmed by IPÌLẸ̀. Do not use a wildcard or accept arbitrary senders. Add only domains verified against actual bank alert samples.

## Deploy

1. Confirm an owned domain is onboarded to Cloudflare Email Routing.
2. Set `BACKEND_URL` in `wrangler.toml` to the active IPÌLẸ̀ API origin.
3. Set the two secrets above.
4. Deploy with `npx wrangler deploy`.
5. Create a Cloudflare Email Routing rule for each generated household recipient pattern, or use a carefully scoped Worker route for the dedicated inbound subdomain. Do not enable a catch-all on the apex domain.
6. Test with an allowlisted bank alert and a second household.

## Safety

- Sender domain allowlist and SPF/DKIM/DMARC authentication are required; the Worker fails closed if missing.
- Household token is validated as an opaque recipient token; the API resolves its SHA-256 hash to one enabled household mailbox.
- The API must enforce message-ID idempotency and create only pending-review imports.
- Attachments are reported as metadata only; they are never executed or trusted as transaction content. Upload statements through the authenticated IPÌLẸ̀ statement-upload UI.
- No balance changes occur at email receipt time.
