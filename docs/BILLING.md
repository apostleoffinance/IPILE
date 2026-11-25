# Billing readiness and payment acceptance

## Current implementation — pilot only

IPÌLẸ̀ currently stores household `plan` and `billing_status` fields and exposes:

| Endpoint | Current behavior |
|---|---|
| `GET /api/v1/billing` | Returns the household plan snapshot |
| `POST /api/v1/billing/plan` | Owner can change the plan label in-app |
| `POST /api/v1/billing/webhook` | Shared-secret audit stub; not a payment processor |

The current webhook accepts a shared secret and records an audit event. It does **not** verify Paystack or Stripe signatures, reconcile a payment, deduplicate provider event IDs, issue receipts, handle refunds, or enforce subscription lifecycle state.

**A plan label is not evidence of payment.** Do not sell or advertise paid access as active until a real provider integration and the acceptance cases below are complete. Keep the product in pilot/free mode in the meantime.

## Required provider integration

Choose one provider and implement its server-side integration:

- Paystack: initialize checkout server-side; verify `x-paystack-signature` using HMAC SHA-512 over the raw body; verify transaction status server-side before granting entitlements.
- Stripe: use Checkout/Customer Portal; verify `Stripe-Signature` against the raw body with the endpoint signing secret.

For either provider:
1. Persist provider customer/subscription IDs against the household.
2. Persist processed webhook event IDs with a unique constraint.
3. Verify signature before parsing/processing the event.
4. Make webhook processing idempotent under retries and concurrent delivery.
5. Reconcile payment amount, currency, household, plan and provider status.
6. Handle pending, active, past-due, canceled, expired and refunded states.
7. Grant entitlements only from verified server-side payment/subscription state.
8. Record an audit event for every billing state transition.
9. Provide customer-visible receipts, renewal/cancellation terms and refund route.
10. Never expose provider secret keys in frontend bundles or logs.

## Required sandbox acceptance

- Successful checkout activates only the intended household.
- Failed/canceled checkout grants no paid entitlement.
- Invalid signature is rejected.
- Duplicate event delivery changes state once.
- Out-of-order events cannot reactivate a canceled/expired subscription.
- Wrong amount/currency/household mapping is rejected and alerted.
- Refund and chargeback revoke or adjust entitlements according to policy.
- Customer cancellation stops renewal and is reflected in the app.
- Reconciliation job detects provider/app state mismatch.

## Launch gate

Until all required cases pass in provider sandbox and the live cutover is approved, label plans accurately as pilot access and do not collect subscription payments.


## Pilot-mode enforcement

As of the operational-readiness follow-up, paid plan activation is explicitly disabled in the billing service. The owner-only plan endpoint may retain a household on the `pilot` plan, but requests to activate `family` are rejected until a verified payment integration is implemented and separately reviewed. The plan catalogue labels Family as planned/unavailable. The webhook remains an audit-only stub and cannot grant paid entitlements.

Do not remove this guard or enable `PAID_PLANS_ENABLED` as a configuration shortcut. The release must include provider checkout, signature verification, idempotent event handling, reconciliation and lifecycle acceptance described above.
