# Statement extraction worker

Statement uploads are persisted as jobs in PostgreSQL and processed outside the API process.

## Render Background Worker

Create a **Background Worker** using the same repository and the same environment group as the API:

- Root directory: `backend`
- Build command: `pip install -e .`
- Start command: `python -m app.workers.statement_extraction`
- Instance: at least 1 GB RAM; one worker process per instance
- Required shared environment: `DATABASE_URL` and the same application secrets/configuration used by the API

The worker and API must use the same database. Do not run multiple worker processes inside one small instance. PostgreSQL row locks with `SKIP LOCKED` allow horizontal scaling later without double-claiming tasks.

## Processing lifecycle

1. The API validates the upload size and account ownership.
2. The original file is stored in a short-lived database task row and an import job is returned immediately.
3. The worker claims one task, extracts it through `statement_intelligence.engine.extract_statement`, validates the result and stages rows for review.
4. The original file bytes are cleared after processing. A stale claim is eligible for recovery after 15 minutes.
5. The frontend polls the household-scoped import job endpoint. Only explicit user approval can post staged rows to the ledger.

If the worker is not running, jobs remain queued and the API remains available. Do not deploy the asynchronous upload endpoint without starting this worker.
