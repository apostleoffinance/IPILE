# IPÌLẸ̀ statement processing on Cloudflare

This is a separate Worker from the production Next.js Worker `ipile-web`. It owns statement queue dispatch, workflow orchestration and the Container Durable Object. It must not replace or modify the frontend Worker.

## Components

- PostgreSQL remains the durable source of truth for upload bytes, task state and import-review state.
- Queue messages contain only a task UUID and schema version. Never put statement bytes or personal financial data in Queue messages.
- Workflows provide bounded retries and durable orchestration.
- A task-specific Durable Object starts the Python backend container from the existing `backend/Dockerfile`.
- The backend extraction engine remains authoritative; transaction staging and review remain in PostgreSQL.
- The frontend continues to poll the existing household-scoped import-job API. No extraction result may post ledger transactions without explicit user approval.

## Required secrets

Set these as Worker secrets before deployment:

- `INTERNAL_API_SECRET`: a long random secret shared only with the backend's internal processing endpoint.
- The backend database connection must be supplied to the container as a dedicated secret/binding. Do not use `BACKEND_URL` as a database credential.

## Deployment prerequisites

1. Confirm the Cloudflare account has Workers Paid and Containers enabled.
2. Create Queues `ipile-statement-jobs` and `ipile-statement-jobs-dlq` in the Cloudflare account before the first deploy.
3. Configure the API-to-Worker dispatch secret and URL.
4. Verify the image build context resolves the repository's existing backend Dockerfile and backend dependency files. Wrangler must build the container image in CI with Docker enabled.
5. Deploy this service separately from `ipile-web`.

## Safety gate

Do not route production uploads to this Worker until the backend internal task-claim endpoint, transactional outbox/recovery path, task idempotency, and large-PDF acceptance tests are in place. Until then, keep the existing PostgreSQL worker path active.
