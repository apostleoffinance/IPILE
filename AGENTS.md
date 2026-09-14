# Agent instructions

IPÌLẸ̀ (code name: Family Finance OS) is a configurable household financial operating system — not an MVP, not an expense tracker, and not a product defined by the founders' household.

1. Read `PRODUCT_SPEC.md` before writing code. It is the source of truth (v1.1.0+).
2. Read `PHASE_STATUS.md`. Implement **only** the current phase.
3. Read `IMPLEMENTATION_ROADMAP.md` for scope and definition of done.
4. Complete one phase fully (tests + DoD + status update) before the next.
5. Every financial query is scoped by `household_id`.
6. Financial math is deterministic, decimal-based, and tested. AI never invents figures.
7. Rules are data. Do not hardcode tithe, religion, "baby", salon, or other household-specific concepts.
8. Litmus: if a feature works only for the founding family, it is household configuration — not an IPÌLẸ̀ feature.
9. No mock mode. Seed data is a normal household (Tenant #1).
10. Modular monolith: FastAPI + Next.js + PostgreSQL.
11. Do not commit secrets.
