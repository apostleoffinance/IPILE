# IPÌLẸ̀ Connect — Cloudflare inbound bank-alert setup

This runbook configures Cloudflare Email Routing and the dedicated `ipile-inbound-email` Worker. It does not change the MX records for the root domain or the existing website Worker.

## 1. Inbound email domain

Use the dedicated subdomain `inbox.ipile.app`. Household addresses take this form:

```text
bank-alert+<opaque-household-token>@inbox.ipile.app
```

In each IPÌLẸ̀ backend environment (Render), configure:

- `INBOUND_EMAIL_DOMAIN=inbox.ipile.app`
- `INBOUND_EMAIL_WEBHOOK_SECRET`: a unique random secret of at least 32 random bytes

Keep the secret server-side. Never place it in a frontend variable or commit it to Git.

## 2. Initial supported sender domains

The following 17 trusted root domains are sourced from the operator-provided bank sender CSV. Configure the Worker secret `ALLOWED_BANK_SENDER_DOMAINS` with this comma-separated value:

```text
gtbank.com,accessbankplc.com,zenithbank.com,firstbanknigeria.com,ubagroup.com,fidelitybank.ng,stanbicibtc.com,fcmb.com,sterling.ng,wemabank.com,alat.ng,moniepoint.com,kuda.com,opayweb.com,opay-inc.com,opay-nigeria.com,palmpay.com
```

This covers the 14 institutions in the CSV:

| Institution | Trusted root domain(s) | Common alert sender address(es) |
|---|---|---|
| GTBank (GTCO) | `gtbank.com` | `GeNS@gtbank.com` |
| Access Bank | `accessbankplc.com` | `no_reply@accessbankplc.com` |
| Zenith Bank | `zenithbank.com` | `ebusiness@zenithbank.com`, `alerts@zenithbank.com` |
| First Bank | `firstbanknigeria.com` | `FirstContact@firstbanknigeria.com` |
| UBA | `ubagroup.com` | `alerts@ubagroup.com`, `no-reply@ubagroup.com` |
| Fidelity Bank | `fidelitybank.ng` | `alerts@fidelitybank.ng`, `noreply@fidelitybank.ng` |
| Stanbic IBTC | `stanbicibtc.com` | `alerts@stanbicibtc.com`, `noreply@stanbicibtc.com` |
| FCMB | `fcmb.com` | `alerts@fcmb.com`, `noreply@fcmb.com` |
| Sterling Bank | `sterling.ng` | `alerts@sterling.ng`, `noreply@sterling.ng` |
| Wema Bank / ALAT | `wemabank.com`, `alat.ng` | `alerts@wemabank.com`, `no-reply@alat.ng` |
| Moniepoint | `moniepoint.com` | `no-reply@moniepoint.com` |
| Kuda Bank | `kuda.com` | `no-reply@kuda.com` |
| OPay | `opayweb.com`, `opay-inc.com`, `opay-nigeria.com` | `no-reply@opayweb.com`, `alerts@opay-inc.com`, `no-reply@opay-nigeria.com` (observed by operator) |
| PalmPay | `palmpay.com` | `no-reply@palmpay.com` |

**Important:** the Worker currently enforces the trusted root-domain allowlist (not a per-address sender allowlist). It also requires Cloudflare's trusted DMARC result to pass. The sender addresses above are reference formats from the supplied CSV, not a guarantee that every institution always uses only those addresses. Verify real original alert samples before tightening to exact sender addresses or changing a bank's parser. This is an initial trusted-sender allowlist. The alert parser recognizes supported ISO currency codes and unambiguous currency symbols; verify bank-specific formats before enabling automatic posting.

## 3. Configure and deploy the Email Worker

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
4. Use the exact comma-separated sender-domain list above for both environments. Never commit webhook secrets.
5. Deploy staging with `npx wrangler deploy`. Deploy production only after the backend production secret/domain and approved sender list have been configured: `npx wrangler deploy --env production`.

The default Worker environment targets the IPÌLẸ̀ staging API. The named `production` environment targets the production API. Do not copy production secrets into staging or vice versa.

## 4. Configure Cloudflare Email Routing

1. Open the Cloudflare dashboard for `ipile.app` and enable Email Routing for the dedicated `inbox.ipile.app` subdomain.
2. Add a routing rule for the base recipient `bank-alert@inbox.ipile.app`.
3. Choose **Send to a Worker** and select the matching `ipile-inbound-email` Worker environment.
4. Ensure plus-address/subaddress delivery is preserved so recipients of the form `bank-alert+<opaque-token>@inbox.ipile.app` are delivered to the same Worker rule.
5. Do not configure an apex-domain catch-all or replace the root domain's existing MX records.

## 5. Verify the household flow

1. Confirm the chosen backend environment has `INBOUND_EMAIL_DOMAIN=inbox.ipile.app` and `INBOUND_EMAIL_WEBHOOK_SECRET` set and is healthy.
2. Sign in to a disposable IPÌLẸ̀ household and open **Money → Import transactions**.
3. Generate the household's private bank-alert address.
4. Forward an original bank transaction alert from an allowlisted bank sender.
5. Confirm the alert appears in **Review incoming bank alerts**.
6. Confirm duplicate delivery of the same provider `MessageID` does not create another review item.
7. Approve the alert against the correct household account and verify the transaction and resulting account balance.
8. Repeat with a second household and verify mailbox and review-queue isolation.

## 6. Security and behavior

- Each household receives a random opaque alias. The backend stores only its SHA-256 hash. Regenerating the address invalidates the previous alias.
- The Worker rejects senders outside the configured trusted root-domain allowlist and messages without a passing sender-authentication result.
- The backend webhook requires the shared secret. Keep the Worker secret and backend secret identical within the same environment.
- The backend deduplicates provider message IDs per household.
- The default mode sends alerts to review. If an owner/partner opts into automation, only alerts with a verified sender, unique exact account match and explicit matching currency may be posted automatically; ambiguous alerts remain in review.
- Ambiguous amounts, multiple currency amounts, unclear debit/credit direction or missing usable dates are rejected into the review queue rather than guessed.
- Attachments are metadata only and are not parsed or executed. Statement attachments must be uploaded separately through the authenticated statement-import flow.
- The parser recognizes a defined set of ISO 4217 codes and unambiguous currency symbols. Ambiguous dollar symbols remain unassigned until the user confirms the destination account currency.
- Avoid forwarding unrelated sensitive email to a household's import address.


## 7. Gmail read-only connection (Phase 1)

Gmail is the preferred connection experience. IPÌLẸ̀ requests only the
`https://www.googleapis.com/auth/gmail.readonly` scope. It does not request
permission to send, modify, or delete messages. Refresh tokens are encrypted
at rest with a dedicated Fernet key and are household-scoped.

Create a Google OAuth 2.0 Web application client and register the exact callback:

`https://<API-HOST>/api/v1/imports/gmail/callback`

Configure these backend environment variables separately for staging and production:

- `GMAIL_OAUTH_CLIENT_ID`
- `GMAIL_OAUTH_CLIENT_SECRET`
- `GMAIL_OAUTH_REDIRECT_URI` (must exactly match the Google OAuth client)
- `GMAIL_TOKEN_ENCRYPTION_KEY` (Fernet key; generate with Python's `Fernet.generate_key()`)
- `GMAIL_SYNC_SECRET` (long random secret shared only with the scheduled Worker)
- `GMAIL_ALLOWED_SENDER_DOMAINS` (comma-separated trusted bank root domains)

The sender-domain list should contain only domains verified from original bank
alerts. The existing Nigerian-bank reference list is in section 2. Do not
configure a broad wildcard or accept all senders.

The Worker runs a scheduled sync every five minutes. Set the matching
`GMAIL_SYNC_CRON_SECRET` Worker secret for each environment; its value must
match that environment's backend `GMAIL_SYNC_SECRET`. The scheduled event calls
the backend's authenticated Gmail sync endpoint. The first sync scans the
previous seven days; subsequent syncs use the last processed Gmail message
timestamp and deduplicate by Gmail message ID and bank transaction identity.

The user can also request a one-time sync from **Money → Import transactions**.
Disconnecting removes the encrypted refresh token from IPÌLẸ̀. Users can also
revoke IPÌLẸ̀ from their Google Account security settings.

Google OAuth consent-screen verification and publishing status are controlled
in the Google Cloud project. Do not enable the connection for general users
until the consent screen, production callback, privacy disclosures and required
Google verification are complete.

## 8. Automation and currency behavior

Household owners/partners can select:

- `review_everything`: every supported alert waits for approval (default).
- `auto_trusted`: automatically posts only when sender verification, a unique
  exact institution-to-account match and an explicit matching currency are all
  present.
- `full_automation`: uses the same non-negotiable safety gate for supported
  alert formats; ambiguous sender, account, amount, date or currency still
  goes to review or is rejected. It never guesses an account or exchange rate.

The bank-alert parser recognizes supported ISO 4217 currency codes and
unambiguous symbols. A bare dollar sign is ambiguous and is not assigned a
currency automatically. The selected account currency must match a detected
alert currency before approval. This does not convert currencies or rewrite
historical ledger amounts; cross-currency conversion remains the responsibility
of the existing exchange-rate and reporting workflows.

Automatic forwarding remains an alternative: users generate the private
household address and configure a provider-side forwarding/filter rule once.
The Worker accepts only authenticated bank sender domains; do not forward
unrelated personal mail. Some email providers require a forwarding-address
verification step, so users should complete that provider-specific verification
before relying on the rule.

## 9. Phase 1 environment checklist

- [ ] Configure Google OAuth Web client, consent screen and exact callback URI.
- [ ] Set the five Gmail backend secrets/settings above on staging.
- [ ] Set `GMAIL_SYNC_CRON_SECRET` on the staging Worker.
- [ ] Confirm the Worker secret equals the staging backend `GMAIL_SYNC_SECRET`.
- [ ] Configure trusted sender domains on the staging backend.
- [ ] Deploy and verify the staging Worker scheduled trigger.
- [ ] Connect a disposable Gmail account and verify that only bank-alert senders
      with DMARC pass are imported.
- [ ] Verify five-minute scheduled sync, duplicate handling, disconnect and
      reauthorization.
- [ ] Repeat configuration independently for production only after approval.
