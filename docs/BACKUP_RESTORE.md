# Production database backup and restore runbook

**Important:** these commands are an operator runbook, not proof that a provider backup policy is enabled. Record provider, instance, backup point, retention and restore evidence in `docs/OPERATIONAL_READINESS.md`.

## 1. Confirm the correct database

- Confirm the production service's `DATABASE_URL` points to the IPÌLẸ̀ production PostgreSQL instance.
- Do not print the URL or its password in shell history, CI logs, chat, screenshots or tickets.
- Confirm database provider, project/instance ID, region, TLS requirement and owner.
- The database must be managed PostgreSQL; a container filesystem or local SQLite file is not an acceptable production database.

## 2. Required backup policy

- Automated daily backups, minimum 7 daily restore points.
- Prefer point-in-time recovery (PITR); target RPO ≤ 24 hours.
- Encrypt backups at rest and in transit.
- Restrict restore/export privileges to designated operators.
- Alert on missing/failed backups and retention expiry.
- Store database backups and application secrets separately.
- Never store secrets in a database dump or repository.

## 3. On-demand logical backup

Run from a trusted operator environment with PostgreSQL client tools and a protected destination. Use a secret manager or interactive password prompt; do not place credentials in command arguments.

```bash
umask 077
pg_dump --format=custom --no-owner --no-acl \
  --file="ipile-$(date -u +%Y%m%dT%H%M%SZ).dump" \
  "$DATABASE_URL"
```

Record the dump checksum and storage object identifier. Verify the dump can be listed:

```bash
pg_restore --list ipile-YYYYMMDDTHHMMSSZ.dump >/dev/null
sha256sum ipile-YYYYMMDDTHHMMSSZ.dump
```

Do not upload dumps to public buckets or attach them to CI artifacts.

## 4. Isolated restore drill

Never restore over production during a drill.

1. Provision a temporary isolated PostgreSQL database with the same major version or a supported upgrade path.
2. Restore into that target:
   ```bash
   createdb "$RESTORE_DATABASE_NAME"
   pg_restore --exit-on-error --no-owner --no-acl \
     --dbname="$RESTORE_DATABASE_URL" ipile-YYYYMMDDTHHMMSSZ.dump
   ``
3. Verify schema and migration head:
   ```bash
   psql "$RESTORE_DATABASE_URL" -X -v ON_ERROR_STOP=1 \
     -c 'SELECT version_num FROM alembic_version'
   ```
4. Compare table counts and aggregate financial totals to a pre-backup manifest. Use aggregate values only; do not copy customer PII into evidence.
5. Start a staging API pointed only at the restore target.
6. Verify readiness, login with synthetic test users, account/transaction reads, export, and cross-household denial.
7. Record restore start/end times, backup timestamp, migration head, checksums, aggregate checks and any differences.
8. Destroy the temporary database after review and retain the evidence record.

## 5. Recovery objectives

Pilot targets:

- **RPO:** no more than 24 hours of committed data loss.
- **RTO:** restore core service within 4 hours.

Measure actual restore time. If provider backup granularity or restore duration cannot meet these targets, document the gap and do not certify the release.

## 6. Local development only

Docker Compose may be used to validate the mechanics of `pg_dump` / `pg_restore`:

```bash
docker compose exec -T postgres pg_dump -U familyos -d familyos \
  --format=custom --file=/tmp/familyos.dump
docker compose cp postgres:/tmp/familyos.dump ./backups/familyos-local.dump
docker compose exec -T postgres pg_restore -U familyos -d familyos \
  --clean --if-exists /tmp/familyos.dump
```

A local drill does not replace a production provider backup or isolated production restore.

## 7. Sign-off record

Record provider/instance (not credentials), backup policy, latest backup timestamp, restore target, source backup ID, schema head, aggregate validation, measured RPO/RTO, operator and evidence URL in `docs/OPERATIONAL_READINESS.md`.
