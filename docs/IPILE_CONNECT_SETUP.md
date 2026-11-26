# IPÌLẸ̀ Connect — Cloudflare inbound bank-alert setup

This runbook configures Cloudflare Email Routing and the dedicated `ipile-inbound-email` Worker. It does not change the MX records for the root domain or the existing website Worker.

## 1. Choose a dedicated inbound subdomain

Use a domain controlled by the IPÌLẸ̀ operator, for example `inbox.<your-owned-domain>`. Do not assume `ipile.app` or any example domain is available; verify ownership and Cloudflare zone access first.

In the IPÌLẸ̀ backend environment (Render), configure:

- `INBOUND_EMAIL_DOMAIN`: the exact inbound subdomain, e.g. `inbox.<your-owned-domain>`
- `INBOUND_EMAIL_WEBHOOK_SECRET`: a unique random secret of at least 32 random bytes

Keep the secret server-side. Never place it in a frontend variable or commit it to Git.

## 2. Configure and deploy the Email Worker

From `cloudflare/email-worker`:

1. Install dependencies with `npm ci`.
2. Run `npm test` and `npm run typecheck`.
3. Set the staging and production Worker secrets separately:
   ```sh
   npx wrangler secret put INBOUND_WEBHOOK_SECRET
   npx wrangler secret put ALLOWED_BANK_SENDER_DOMAINS
   npx wrangler secret put INBOUND_WEBHOOK_SECRET --env production
   npx wrangler secret put ALLOWED_BANK_SENDER_DOMAINS --env production
   ```
4. `ALLOWED_BANK_SENDER_DOMAINS` must be a comma-separated list of exact bank-owned sender domains confirmed from real bank alert samples. Do not use broad wildcards or accept arbitrary senders.
5. Deploy staging with `npx wrangler deploy`. Deploy production only after the backend production secret/domain and approved sender list have been configured: `npx wrangler deploy --env production`.

The default Worker environment targets the IPÌLẸ̀ staging API. The named `production` environment targets the production API. Do not copy production secrets into staging or vice versa.

## 3. Configure Cloudflare Email Routing

1. Open the Cloudflare dashboard for the dedicated inbound subdomain and enable Email Routing.
2. Add a routing rule for the base recipient `bank-alert@inbox.<your-owned-domain>`.
3. Choose **Send to a Worker** and select the matching `ipile-inbound-email` Worker environment.
4. Ensure plus-address/subaddress delivery is enabled so recipients of the form `bank-alert+<opaque-token>@inbox.<your-owned-domain>` are delivered to the same Worker rule.
5. Do not configure an apex-domain catch-all or alter the root domain's existing MX records.

The Worker validates the household alias, sender-domain allowlist and sender authentication result before forwarding a bounded, normalized payload to the backend over HTTPS.

## 4. Verify the household flow

1. Confirm the chosen backend environment has `INBOUND_EMAIL_DOMAIN` and `INBOUND_EMAIL_WEBHOOK_SECRET` set and is healthy.
2. Sign in to a disposable IPÌLẸ̀ household and open **Money → Import transactions**.
3. Generate the household's private bank-alert address.
4. Forward an original bank transaction alert from an allowlisted bank sender.
5. Confirm the alert appears in **Review incoming bank alerts**.
6. Confirm duplicate delivery of the same provider `MessageID` does not create another review item.
7. Approve the alert against the correct household account and verify the transaction and resulting account balance.
8. Repeat with a second household and verify mailbox and review-queue isolation.

## 5. Security and behavior

- Each household receives a random opaque alias. The backend stores only its SHA-256 hash. Regenerating the address invalidates the previous alias.
- The Worker rejects senders outside the configured bank-domain allowlist and messages without a passing sender-authentication result.
- The backend webhook requires the shared secret. Keep the Worker secret and backend secret identical within the same environment.
- The backend deduplicates provider message IDs per household.
- Incoming alerts are pending review. No transaction or balance is changed until an authorized household owner/partner approves the alert.
- Ambiguous amounts, multiple currency amounts, unclear debit/credit direction or missing usable dates are rejected into the review queue rather than guessed.
- Attachments are metadata only and are not parsed or executed. Statement attachments must be uploaded separately through the authenticated statement-import flow.
- The parser currently supports NGN-denominated alert formats. Add and test bank-specific formats before enabling other currencies.
- Avoid forwarding unrelated sensitive email to a household's import address.
