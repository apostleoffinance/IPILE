# Family Finance OS

Household financial operating system. The complete product is defined in [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md). Implementation follows [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) one phase at a time. Current phase: [`PHASE_STATUS.md`](PHASE_STATUS.md).

This is not an MVP and not an expense tracker. The first household is a production tenant using seed data, not a mock mode.

## Local development

```bash
cp .env.example .env
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000/api/v1/health

Postgres is published on host port **5433** (5432 is often already taken locally).

Or run services separately after `docker compose up postgres`:

```bash
cd backend && pip install -e ".[dev]" && alembic upgrade head && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## Seed household

After `docker compose up`, a normal household named **Seed Household** exists.

- Owner: `owner@seed.example.com`
- Partner: `partner@seed.example.com`
- Password: `family-os-seed-owner`

Registering a new user creates a separate household. This is not mock mode.

## Phase 1

Households, members, accounts, categories, income, and manual transactions. Safe to Spend, allocation, and health scores are later phases.
