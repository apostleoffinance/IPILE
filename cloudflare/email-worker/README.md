# IPÌLẸ̀ inbound bank-alert Email Worker

This Worker is separate from the public Next.js Worker. It receives mail through Cloudflare Email Routing, validates the envelope recipient and exact bank sender-domain allowlist, verifies Cloudflare's trusted DMARC result, parses MIME within size limits, and forwards a normalized payload to the existing FastAPI inbound endpoint over HTTPS.

## Required Worker secrets

Set separately for staging and production with Wrangler; never commit values:

```sh
npx wrangler secret put INBOUND_WEBHOOK_SECRET
npx wrangler secret put ALLOWED_BANK_SENDER_DOMAINS
npx wrangler secret put INBOUND_WEBHOOK_SECRET --env production
npx wrangler secret put ALLOWED_BANK_SENDER_DOMAINS --env production
```

`INBOUND_WEBHOOK_SECRET` must match the corresponding backend `INBOUND_EMAIL_WEBHOOK_SECRET`. `ALLOWED_BANK_SENDER_DOMAINS` is a comma-separated list of exact bank-owned sender domains verified from real bank alert samples. Avoid broad or wildcard allowlists.

## Environments and deployment

- Default Worker environment targets `https://ipile-staging-api-v2.onrender.com`.
- The `production` environment targets `https://ipile-bmfz.onrender.com`.
- Run `npm install`, `npm run typecheck`, `npm test` and `npx wrangler deploy --dry-run` before deployment.
- Deploy staging with `npx wrangler deploy`.
- Deploy production only after the production backend domain and secret are configured: `npx wrangler deploy --env production`.

## Cloudflare Email Routing

1. Onboard a dedicated inbound subdomain owned by IPÌLẸ̀, e.g. `inbox.<owned-domain>`.
2. Configure the backend `INBOUND_EMAIL_DOMAIN` to that exact subdomain.
3. Create a Cloudflare Email Routing rule for `bank-alert@inbox.<owned-domain>`, choose **Send to a Worker**, and select the corresponding Worker environment.
4. Verify that plus-addressing preserves `bank-alert+<opaque-token>@...` in the Worker envelope recipient.
5. Do not create an apex catch-all or replace the root domain's existing MX records.

## Security behavior

- Cloudflare prepends its own `Authentication-Results` header. The Worker reads the first result from `message.headers`, verifies the authentication service is `mx.cloudflare.net`, and requires `dmarc=pass`. It does not trust similarly named headers parsed from the sender-controlled raw MIME.
- The sender must also match an exact configured bank domain (or a subdomain of that exact domain).
- The recipient must contain a sufficiently long opaque household token. The API resolves only its SHA-256 hash to an enabled mailbox.
- The Worker enforces a bounded raw email size and attachment size. Attachments are metadata only; they are never parsed as transaction content.
- The backend webhook requires the shared secret and deduplicates provider Message IDs per household.
- Alerts enter the household review queue. No account balance or transaction ledger is changed until an authorized household owner/partner approves the alert.
- The parser currently recognizes NGN alert amounts and common debit/credit wording. Extend and test bank-specific formats before enabling other currencies.
