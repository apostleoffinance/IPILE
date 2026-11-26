# IPÌLẸ̀ frontend on Cloudflare Workers

Cloudflare Workers is the sole supported frontend deployment target. The Next.js 15 application is adapted for Workers with OpenNext.

## Architecture

- Frontend: Next.js 15 / React 19, deployed to Cloudflare Workers through `@opennextjs/cloudflare`.
- API: FastAPI service on Render.
- Database: Neon PostgreSQL.
- API requests: same-origin `/api/v1/*` requests are forwarded by the Next.js route handler to the configured backend origin.

## Local setup and build

Run these commands from `frontend/`:

```bash
npm ci
npm run cf:install
npm run typecheck
npm test
npm run cf:build
npm run cf:preview
```

`cf:install` installs the Cloudflare adapter and Wrangler without adding them to the application's dependency manifest or changing the normal Next.js lockfile.

## Cloudflare Worker configuration

Set this Worker secret in Cloudflare (Settings → Variables and Secrets):

- `BACKEND_URL`: HTTPS base URL of the FastAPI service, without a trailing slash.

The same-origin Worker proxy uses this value at request time. Keep database URLs, session signing keys, billing webhook secrets, and other backend secrets exclusively in the backend environment.

## Staging deployment

The GitHub Actions workflow **Deploy IPÌLẸ̀ Cloudflare staging** deploys merged frontend changes from `main` to the isolated Worker `ipile-web-staging`. It binds `BACKEND_URL` to `https://ipile-staging-api-v2.onrender.com`, checks backend liveness/readiness before deployment, and smoke-tests the deployed homepage and same-origin API health proxy. It runs automatically when frontend files or the staging workflow change on `main`; it can also be started manually with `workflow_dispatch`.

The staging Worker is separate from production. It must never reuse the production Worker name or production backend URL. The workflow uses the repository-level `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets listed below.

## Production deployment

The GitHub Actions workflow **Deploy IPÌLẸ̀ Cloudflare production** is manually dispatched and requires the explicit `approve_production_frontend_deployment` boolean input. It deploys the existing Worker `ipile-web` and sets `BACKEND_URL` to `https://ipile-bmfz.onrender.com`. It checks the production backend before deployment and smoke-tests the deployed Worker and same-origin API proxy afterwards. It does not run database migrations or seed data.

Required GitHub Actions repository secrets:

- `CLOUDFLARE_API_TOKEN`: scoped Cloudflare API token with permission to edit Workers scripts and read the account.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.

Run the production workflow manually from GitHub Actions and select `main`. Its explicit `APPROVE_PRODUCTION_FRONTEND_DEPLOYMENT` input remains mandatory.

## Release validation

Before treating production as ready:

1. GitHub Actions passes frontend typecheck/tests, Next.js build, OpenNext Worker build, and local Worker runtime smoke tests.
2. Confirm the Worker is deployed and its `workers.dev` or approved custom domain route is enabled.
3. Verify landing page, CSRF bootstrap, login, logout, session cookie behavior, and authenticated `/api/v1/auth/me`.
4. Verify household onboarding and representative read/write workflows.
5. Verify file upload/import request bodies, response headers, redirects, and multiple `Set-Cookie` headers through the proxy.
6. Confirm browser console/network logs have no hydration, asset, CORS, or cookie errors.

Do not run production database migrations or seed data as part of the frontend deployment.
