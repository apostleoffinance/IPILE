# IPÌLẸ̀ frontend on Cloudflare Workers

The Next.js application remains a Next.js 15 application; OpenNext adapts its production build for Cloudflare Workers. Cloudflare Workers is the sole supported deployment target.

## Architecture

- Frontend: Next.js 15 / React 19, deployed to Cloudflare Workers through `@opennextjs/cloudflare`.
- API: existing FastAPI service on Render. It is not moved or modified by this milestone.
- Database: existing Neon PostgreSQL database. No schema or data operation is part of this migration.
- API requests: same-origin `/api/v1/*` requests are proxied by the existing Next.js route handler or configured rewrite.

OpenNext is used here instead of vinext because this milestone prioritizes preserving the existing Next.js runtime and route behavior during a production migration. Cloudflare currently recommends vinext for new migrations, but documents it as beta; reconsider it separately after the existing application has been validated on Workers.

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

The Worker is configured in `wrangler.jsonc`. It intentionally has no custom domain or production route configured. The first deployment must be a preview on the `workers.dev` hostname.

Set the following Worker variable in Cloudflare (Settings → Variables and Secrets):

- `BACKEND_URL`: the HTTPS base URL of the FastAPI service, without a trailing slash (for example, the Render service origin).

This value is configuration, not a credential, so it can be a plain-text Worker variable. Do not put database URLs, session signing keys, billing webhook secrets, or other backend secrets in the frontend Worker. Those remain exclusively in the backend environment.

The Worker uses `nodejs_compat_populate_process_env` so the existing `process.env.BACKEND_URL` access in Next.js server code resolves from the Worker binding. Do not expose `BACKEND_URL` as a `NEXT_PUBLIC_*` variable.

If any `NEXT_PUBLIC_*` variables are introduced later, they must be present in the Cloudflare build environment because Next.js inlines them at build time.

## Preview deployment

Authenticate the Cloudflare CLI, then build and preview locally:

```bash
npx wrangler login
npm run cf:build
npm run cf:preview
```

For a repeatable remote preview, add these **GitHub repository Actions secrets** under Settings → Secrets and variables → Actions:

- `CLOUDFLARE_API_TOKEN`: a scoped Cloudflare API token with permission to edit Workers scripts and read the account.
- `CLOUDFLARE_ACCOUNT_ID`: the Cloudflare account ID.
- `IPILE_STAGING_BACKEND_URL`: the HTTPS origin of a staging FastAPI service backed by an isolated staging Neon branch.

Then run the **Deploy IPÌLẸ̀ Cloudflare preview** workflow manually from the Actions tab. It deploys a separate `ipile-web-preview` Worker on `workers.dev`, sets its backend origin, and publishes the preview. It does not configure a custom domain or touch production traffic.

The preview Worker must have `BACKEND_URL` configured before API smoke tests. Do not point a preview at a production database for write-flow testing. Use a staging FastAPI service and isolated staging Neon branch for registration, household creation, imports, and all other mutating acceptance tests.

## Required release validation

Before merging this milestone:

1. GitHub Actions passes: normal frontend typecheck/tests, Next.js production build, OpenNext Worker build, and local Worker startup.
2. Deploy a remote `workers.dev` preview using the dedicated preview Worker name.
3. Configure the preview Worker's `BACKEND_URL` to the staging FastAPI service.
4. Verify unauthenticated landing page, login, logout, CSRF bootstrap, session cookie behavior, authenticated `/api/v1/auth/me`, and the API health endpoint.
5. Verify household onboarding and representative read/write workflows against staging only: accounts, transactions, budgets, obligations, and household switching.
6. Verify file upload/import request bodies, response headers, redirects, and multiple `Set-Cookie` headers through the proxy.
7. Confirm browser console/network logs have no hydration, asset, CORS, or cookie errors.
8. Record the preview URL and test evidence in the pull request.

Do not merge or switch DNS until these checks pass. Do not run production database migrations or seed data as part of this frontend move.

## Production cutover and rollback

After merge and approval:

1. Deploy the same tested commit to the production Worker.
2. Configure the production Worker `BACKEND_URL` to the existing Render API.
3. Add the production custom domain in Cloudflare only after confirming DNS ownership and the exact intended hostname.
4. Verify login and read-only production health immediately after cutover, then monitor errors and latency.
5. Keep the previous DNS and domain configuration documented until the Cloudflare cutover is verified. Rollback requires restoring the previously active DNS routing; this repository does not maintain a second frontend hosting provider.

The current Vercel URL is not assumed to be the final custom domain. No DNS or domain changes are performed by this repository configuration.
