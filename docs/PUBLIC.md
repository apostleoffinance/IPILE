# Public product docs

**IPÌLẸ̀** — the financial foundation for households everywhere.

IPÌLẸ̀ is a household financial operating system: income → allocation → obligations → Safe to Spend → health. Your household's rules are configuration; the engines are universal.

## Get started

1. Register at `/login` (Create account).
2. A household is created for you automatically, or accept an invite token.
3. Add an account, record income, and open Overview.
4. Refine your Family Financial Constitution (allocation rules, buffer, obligations) under Plan.

## Invites

Owners invite partners, members, or viewers from Settings → Invites. The invitee signs in with the invited email and accepts the token.

## Billing

Plans:

- **Pilot** — ₦0 / month (private pilot)
- **Family** — ₦15,000 / month (public family plan placeholder; payment provider wired later)

Owners change plans under Settings → Billing.

## Support

Open a ticket from Settings → Support or `/help`. Tickets are stored server-side and audited.

## Deleting the pilot seed

The seed household is Tenant #1 — a normal household. Soft-deleting it does not require a code fork. Startup seed will not resurrect a deleted `seed-household` slug. Set `SEED_ON_START=false` to skip seeding entirely.
