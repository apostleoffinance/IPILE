# Backup and restore drill

Family Finance OS stores all durable state in PostgreSQL. Phase 13 documents an automated backup path and a restore drill.

## What to back up

- PostgreSQL database `familyos` (all households, sessions, audit logs)
- Application secrets from the environment / secret manager (never from git)

Do not back up only application containers; images are rebuildable from source.

## Local / compose dump (daily or on demand)

```bash
# From the repo root while compose is up
docker compose exec -T postgres \
  pg_dump -U familyos -d familyos --format=custom --file=/tmp/familyos.dump

docker compose cp postgres:/tmp/familyos.dump ./backups/familyos-$(date +%Y%m%d).dump
```

Retain at least 7 daily dumps for the private pilot. Production should use the managed Postgres automated backup schedule (PITR where available).

## Restore drill (evidence)

1. Stop the API so writers are idle: `docker compose stop backend`
2. Create an empty restore database (or a separate volume for the drill).
3. Restore:

```bash
docker compose exec -T postgres \
  pg_restore -U familyos -d familyos --clean --if-exists /tmp/familyos.dump
```

4. Start API: `docker compose start backend`
5. Verify: `GET /api/v1/health` → `ok`; login as seed owner; `GET /api/v1/accounts` returns expected balances; `GET /api/v1/export` returns transaction rows.

## Production notes

- Prefer managed backups (RDS / Cloud SQL / Neon / Supabase) with encryption at rest.
- Test restore into a staging project quarterly; record date and operator in the ops log.
- After restore, rotate `secret_key` only if the dump may have been exposed; otherwise keep sessions valid.
- HTTPS remains terminated at the edge; the database is not exposed publicly.
