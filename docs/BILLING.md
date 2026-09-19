# Billing (PSP-ready)

IPÌLẸ̀ currently tracks household `plan` and `billing_status` in-app without charging a card.
This document explains how to wire **Paystack** or **Stripe** later without changing tenancy.

## Current surface

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/billing` | Plan snapshot for owner/partner |
| `POST /api/v1/billing/plan` | Switch plan in-app (owner) |
| `POST /api/v1/billing/webhook` | PSP webhook stub |

Plans today: `pilot` (₦0) and `family` (list price in `app/services/billing.py`).

## Webhook stub

`POST /api/v1/billing/webhook`

1. Set env `BILLING_WEBHOOK_SECRET` (settings field `billing_webhook_secret`).
2. If the secret is empty, the endpoint returns **503** (not configured).
3. Callers must send header `X-Billing-Secret` matching the configured value.
4. On success the event is written to `audit_logs` (`entity_type=billing`, `action=webhook`) and the API returns **202**.

This is intentionally provider-agnostic. Replace the shared-secret check with the PSP’s signature scheme when you go live.

## Wiring Paystack later

1. Create a Paystack plan / subscription for the Family tier.
2. On checkout success, map `customer_code` / `subscription_code` → `household_id` (store on household or a `billing_customers` table).
3. Point Paystack webhooks at `/api/v1/billing/webhook`.
4. Verify `x-paystack-signature` (HMAC SHA512 of raw body with secret) instead of `X-Billing-Secret`.
5. On `subscription.create` / `charge.success` / `subscription.disable`, update `household.plan` and `household.billing_status`, then `write_audit`.

## Wiring Stripe later

1. Create Products/Prices for Family.
2. Use Checkout or Customer Portal; store `stripe_customer_id` per household.
3. Point Stripe webhooks at the same route (or `/api/v1/billing/webhook/stripe` if you prefer separate paths).
4. Verify `Stripe-Signature` with the webhook signing secret.
5. Handle `customer.subscription.updated` / `deleted` / `invoice.paid` to sync plan + status.

## Security notes

- Never trust client-reported plan changes from the browser alone once PSP is live — prefer webhook + server-side portal.
- Keep secrets in env only; do not commit live keys.
- Webhook handlers must stay idempotent (dedupe by provider event id in audit or a processed-events table).
