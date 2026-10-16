# CI/CD and deploy

Purpose: how CI gates merges, how code reaches staging and production, and how to confirm that what is live is what you meant to ship.
Read when: before touching CI workflows, Dockerfiles, compose files, deploy scripts, environment variables, scheduled jobs or health endpoints, and before reporting a deploy as done.

Ready-to-copy files are in [ci/](../../ci/README.md): [ci.yml](../../ci/workflows/ci.yml), [deploy-staging.yml](../../ci/workflows/deploy-staging.yml), [dependabot.yml](../../ci/dependabot.yml). The merge policy (auto-merge on green CI) is in [git workflow](git-workflow.md#auto-merge-on-green-ci).

The shape of the pipeline:

```
PR -> CI `check` (required) -> auto-merge (squash) -> deploy-staging workflow
   -> post-deploy smoke test -> human runs the production deploy script
   -> same image promoted, prod migrations, smoke test, tag
```

## CI shape

- **One required job, `check`, holding all fast steps.** Why: GitHub bills at least one minute per job; a separate five-second version job costs a full minute on every run.
- **Never put `paths-ignore` on a workflow that hosts a required check.** A skipped required check stays "Expected" and the PR can't merge. Run the job always and skip heavy steps with `if:` when the PR is docs-only ([ci-docs-only.mjs](../../ci/scripts/ci-docs-only.mjs)). Fail safe: anything unclear runs full CI, including markdown that tests read. Why: without the early exit, every docs-only PR pays for the full pipeline.
- **Workflows that are NOT required checks may use a positive path filter (`paths:`)** to save minutes. If one later becomes required, switch it to the early-exit pattern above.
- **Concurrency: CI cancels stale runs per ref; deploys queue and never cancel.**
  ```yaml
  # CI
  concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }
  # deploy
  concurrency: { group: deploy-staging, cancel-in-progress: false }
  ```
  Why: a deploy cancelled half-way leaves half-applied state, and parallel deploys collide.
- **CI runs on `pull_request` only, not again on push to main.** A squash merge of a PR that passed `check` is the same code. Accepted risk: semantic skew between two green PRs, caught by the post-deploy smoke test on staging.
- **Step order: security-boundary guards first, then lint, full typecheck (test files included), tests, build, and the version check last.** Why: the most important failure should be the first one visible, and lint and test results should still show when only the version bump is missing.
- **Set `timeout-minutes` on every job.** Why: a hung step otherwise burns the default six hours of minutes.
- **Check scripts emit GitHub annotations** (`echo "::error file=src/a.ts,line=12::message"`) so failures show on the diff. Stdlib-only scripts need no setup step.
- **Dry-run incident-only scripts in CI** (a post-restore verifier, a data-repair script with `--dry-run`). Why: code that never runs breaks exactly when you need it.
- **Don't add build caching without measuring, and write the before and after numbers down.** Why: a layer cache can make builds slower when exporting the cache costs more than it saves.

## Supply chain and permissions in CI

- **Pin every third-party action to a full commit SHA with a version comment:** `uses: actions/checkout@<40-char sha> # v4.2.2`. Dependabot updates them weekly in one grouped PR that a human merges. Why: a floating tag can be repointed to a malicious commit; pinning freezes security fixes, and Dependabot restores freshness.
- **Default to `permissions: contents: read`, and `persist-credentials: false` on checkouts that don't push.**
- **Pass untrusted event data through `env:`, never inline into `run:`.** `run: echo "${{ github.event.pull_request.title }}"` lets anyone who can open a PR run shell commands in your CI.
- **Install exactly the lockfile and fail on drift:** `pnpm install --frozen-lockfile`, `npm ci`, `uv lock --check` before `uv sync` (which silently rewrites a stale lock; `--locked` fails on a stale lock, `--frozen` doesn't check). In images: `npm ci --omit=dev`, never `npm install`. Why: prod must run the tested dependency tree, and a freshly published compromised patch release must not slip in.
- **Pin the package manager through Corepack** (`"packageManager": "pnpm@x.y.z"` in package.json, `corepack enable` in CI). Why: a third-party setup action can break on CI runners only, while Corepack keeps CI, cloud shells and laptops on the same version.
- **Pin linter and formatter versions.** Why: an unpinned new release fails files nobody touched.
- **Check what the package manager wrote after every add or update.** Some silently add exclusions that bypass supply-chain protections such as a minimum release age; revert them unless you decided otherwise. More in [security](security.md).

## Database in CI

- **Run an ephemeral Postgres at the same major version as production.** Start it in the background so the image pull overlaps dependency install.
- **Recreate the production role split:** the owner role runs migrations and is NOT a superuser (a superuser bypasses row-level security, so isolation tests would pass for the wrong reason); the app role owns nothing and has no `BYPASSRLS`. Each step declares its own connection string so it is visible which role does what. Order: RLS metadata guard, RLS behaviour gate, DB tests. See [database](database.md#multi-tenant-isolation).
- **The throwaway CI database password lives in the workflow file, not in secrets.** Why: a secret suggests it protects something.
- **Build without database access.** If the build starts needing one, CI notices.

## Deploy workflow

- **Deploy is a separate workflow from CI, and it is the only one with `id-token: write`.** Why: CI runs on PR code, possibly from outside the team; the OIDC permission must not exist there. A contract test asserts it ([testing](testing.md#file-level-contract-tests)).
- **Deploy without stored keys:** OIDC / workload identity federation. The deployer identity may push images and deploy staging resources only; GitHub has zero rights over production. A test asserts that no workflow mentions production services, jobs or secrets.
- **If a platform only offers deploy tokens, use one token per app.** Why: a leaked token can't touch the other apps. Add a preflight step that fails loudly when the token secret is missing.
- **The image tag is the commit SHA, never `latest`.** Production promotes the staging image byte-for-byte, with no rebuild; a commit without a staging image can't go to production. Rollback is deploying an older tag.
- **Deploy workflows may use `paths-ignore` as a blacklist** (`docs/**`, `**/*.md`); never ignore `scripts/`, `.github/` or anything the Dockerfile copies. With a positive filter, include every file the Dockerfile `COPY`s (seed data, launch scripts, config), or a merged change silently never deploys.
- **A deploy-on-push workflow doesn't wait for CI.** The required check on main is the real gate; without branch protection, trigger on `workflow_run` of CI instead.
- **Repeat security-boundary guards in the deploy workflow.** Why: a direct push to main bypasses PR checks. Lint and tests stay out: they are quality gates, not leak boundaries.
- **Manual deploys from a laptop are for recovery only; CI is the normal path.**
- **Test non-trivial runtime changes on a branch deployment before merging to main** when the platform supports preview or branch environments.
- **Put explicit project, region and account flags in every infrastructure command.** If a "redeploy" prompts you to create something (for example "allow unauthenticated invocations?"), you are about to create a new resource in the wrong project or region: stop.

## Migrations in the pipeline

- **Staging migrations run automatically before the app deploy, and only when the live schema lags the repo.** Compare the latest migration name AND the migration count; a merge can bring in a migration with an older timestamp. Run them as a one-off job from the new image, with retries off. A failed migration blocks the deploy, and the old revision keeps running on the old schema.
- **The migration job has its own role and secret, which cannot connect to the production database, and refuses any database name but the expected one.**
- **On a PaaS, use the platform's release command** (for example `release_command` in `fly.toml`), never SSH from CI.
- **A deploy pipeline must apply or verify migrations, and a skipped step must look different from a failed one.** Why: otherwise a green run can ship an unmigrated schema or an unmounted secret.
- **Production migrations are a human action**, run by the production deploy script before the app deploy.
- **Sequence deploys around breaking interface changes between layers** (database function signature, API contract): make the contract compatible in both directions first, and don't stack two breaking changes back to back.

## Environment variables and secrets

- **Flags like `--set-env-vars` and `--set-secrets` overwrite the whole set:** list every entry on every deploy.
- **Mount secrets unconditionally,** so a missing secret fails the deploy loudly instead of the service silently running without login or error reporting.
- **Don't gate behaviour on a check the running identity has no permission to perform.** Why: a condition like "mount the secret only if `secrets describe` succeeds" always takes the else path when the deployer can't read secrets, and error reporting is then silently off.
- **A flag that cannot succeed must not stay in the pipeline.** Why: a flag the deployer lacks the rights to apply only prints a warning; it reads like a guarantee and guarantees nothing.
- **A build-time variable missing from the build environment produces a green build and a dead product.** List required build-time variables and fail the build when one is empty.
- **Source uploads read their own ignore file.** For example `gcloud ... --source .` reads `.gcloudignore`, not `.dockerignore`; without one, local key files and `.env` get uploaded. Keep an explicit ignore file per upload tool.
- **Behind reverse proxies, set the trusted-proxy hop count.** Why: otherwise every visitor shares one per-IP rate-limit bucket and legitimate users get locked out.
- **Never print secret values while inspecting an environment;** list names only. Details in [security](security.md).

## Post-deploy smoke test

Runs at the end of every deploy ([deploy-staging.yml](../../ci/workflows/deploy-staging.yml) has the full step):

- `/api/health` with no auth header: proves public traffic reaches the app.
- The live commit SHA equals the commit you deployed.
- Error reporting is armed (the health endpoint reports SDK state).
- Deep health with a token: database connection under the app role.
- Live schema version and migration count equal the repo.
- Webhook routes reject unsigned requests with 401. A 503 means the signing secret isn't mounted.

Print every response body; never use `curl -f`, which swallows the diagnosis. Under `set -euo pipefail`, append `|| true` to a `grep` or `jq` extraction so the error message still prints.

## Health endpoint

- **`/api/health` returns status, environment, version, commit SHA and error-tracker state, and does not touch the database.**
  ```ts
  // app/api/health/route.ts (Next.js)
  import * as Sentry from "@sentry/nextjs";      // or your error tracker
  import { NextResponse } from "next/server";
  import pkg from "@/package.json";
  export const dynamic = "force-dynamic";

  // Report SDK STATE, not env-var presence: a lost secret leaves the service "healthy" with no error reports.
  function errorReporting(): "on" | "off" | "unknown" {
    const client = Sentry.getClient();
    return !client ? "unknown" : client.getDsn() ? "on" : "off";
  }

  export function GET() {
    return NextResponse.json({
      status: "ok",
      environment: process.env.APP_ENV ?? "unknown",
      version: pkg.version,
      commit: process.env.APP_SHA ?? null,
      errorReporting: errorReporting(),
    });
  }
  ```
- **Apps with background workers report worker liveness, and return 503 when a worker is dead.** Add a container `HEALTHCHECK` that calls it.
- **Health routes that open a database connection are token-gated** (constant-time comparison; in a deployed environment a missing token returns 503, never an open route). See [security](security.md).
- **A supervisor tells a crash (restart with backoff) from a clean stop that needs a human (don't restart).** Naive auto-restart of a container that is waiting for re-authentication just loops.

## Containers

- **Boot-check after every image build or deploy:** no service in `Restarting`, the app log shows the listening line and no stack trace, health returns 200, and the version matches. Why: compose prints "Started" for a container that dies immediately, and the test suite never builds the image.
  ```bash
  docker compose ps
  docker compose logs --tail 20 app
  curl -s http://localhost:<port>/health
  ```
- **Dockerfile traps:**
  - `COPY *.js ./` copies top-level files only; modules in subdirectories need their own `COPY`. A missing module crash-loops the container while every test is green. `Cannot find module` / `ModuleNotFoundError` at boot means the image is missing a file.
  - Pin the base image to an exact version (`node:<major.minor.patch>-bookworm-slim`, `python:<major.minor>-slim`), never `latest`, which can change major version silently.
  - Copy the dependency manifests and install before copying the code, so the install layer is cached until dependencies change; copy only lockfile inputs into that layer.
  - Run as a non-root user.
- **Compose traps:**
  - `docker compose restart` does not re-read `.env`; use `docker compose up -d --force-recreate`.
  - Pin the project with a top-level `name:`. Volume names derive from the project name, and running from another directory creates a new, empty volume (the data looks gone).
  - Gate the app on the database healthcheck (`depends_on: { db: { condition: service_healthy } }`).
  - Bind internal services to `127.0.0.1` behind the reverse proxy.

## Scheduled jobs

- **Define an exit-code contract:** exit 0 for "nothing to do" and for partial failures that retry themselves next run; exit 1 for total failure, which triggers the alert.
- **Alarm only when a source fails two runs in a row, and fail the run after publishing,** so healthy sources still update. Why: one miss is noise, and a run that stays green can hide broken sources for weeks.
- **Set `timeout-minutes` and add `workflow_dispatch`** for manual reruns.
- **GitHub disables scheduled workflows in public repos after 60 days without repository activity.** Add a monthly keepalive commit or accept the risk knowingly.
- **For jobs on a machine that may be off, use a catch-up window plus an idempotency check.**
- **Run a new automated job once as a one-off, review the result, and only then make it recurring.**

## Staging parity

- **Staging gets the same runtime flags as production** (CPU, memory, cold-start settings, feature flags). Why: a staging that behaves differently produces false findings.
- **Staging data is realistic and non-personal**, not empty stubs: empty data hides layout and edge-case bugs.
- **Document every channel with no staging twin** (a payment, email or webhook provider shared between environments), where a click on staging writes to production.

## Production deploys

- **A human runs production deploys; agents have no production credentials.** The agent doesn't propose or mention a production deploy during the feature cycle; the product owner initiates it. When asked, the agent prepares the exact command in the handoff format from [collaboration](collaboration.md). Why: there are too many documented cases of AI agents destroying production.
- **Never print a rollback command next to a deploy command unless someone asks.** Why: people run code blocks in order, so a rollback block right below a deploy block gets run right after a successful deploy.
- **Pin the production deploy script by hash in the human's shell alias, with the hash kept outside the repo:**
  ```bash
  alias deploy-prod='cd ~/code/app && git switch main && git fetch origin main && git merge --ff-only origin/main \
    && echo "<sha256>  scripts/deploy-prod.sh" | sha256sum -c --quiet && bash scripts/deploy-prod.sh'
  ```
  Why: a production deploy script runs with production rights, so an unreviewed change to it on main would get those rights on the next deploy; with the pin, a changed script fails the check and doesn't run. Every script change means a new hash (a test asserts the documented hash matches the script), and the PR tells the human to update the alias. The script must not source or execute other repo files, because the pin covers only itself.
- **The production deploy script itself:** requires the expected account and stops otherwise; deploys only commits that are on main; refuses code older than the live database schema; promotes the staging image (no rebuild); runs the production migration job before the app deploy; smoke-tests commit, error reporting and schema; creates the version tag without moving existing ones; prints the rollback command only when it fails.
- **Give production commands names that can't be confused across apps.**
- **Hobby projects with no users may deploy straight to production on every commit.** Don't carry that habit into a product with real users.

## Release flow

1. PR merged to main (auto-merge on green `check`).
2. Staging deploy runs for the merge commit; the smoke test passes.
3. The agent verifies the staging SHA (below) and reports it.
4. Release notes for user-visible changes are drafted, approved and committed before the production deploy ([versioning](versioning.md#release-notes)).
5. The human runs the production deploy script; it migrates, promotes the image, smoke-tests and tags.
6. The agent confirms the production health endpoint reports the expected version and SHA, and checks the main user flow.

## After every deploy

- **Read the repo's documented deploy procedure before deploying, and follow it exactly.** Don't improvise alternative paths.
- **Confirm what is live, tied to your own commit:**
  ```bash
  SHA=$(gh pr view <N> --json mergeCommit -q .mergeCommit.oid)
  gh run list --workflow deploy-staging.yml --commit "$SHA" --json status,conclusion
  curl -s https://staging.example.com/api/health      # "commit" must equal $SHA
  ```
  Report: "Deployed to staging: vX.Y.Z (sha abc1234, confirmed on /api/health)". Never infer it from the UI footer or from "the latest run".
- **Exercise the product's main flow, not just your change,** and check container status and logs. Why: a build missing an environment variable can pass build, lint and deploy while the product is dead, and then a user finds it first.
- **"It doesn't work" after a deploy usually means "it isn't deployed" or "it's cached".** Curl the server for a symbol only the new code has; check the browser cache and service worker; check which directory or branch a preview server is actually serving. Give the user a visible version marker.
- **A failure that moves between runs right after a deploy, with clean server logs, points to timing.** Rerun once while tailing the server log before blaming the code.

## Backups and restore

- **Run a restore drill before relying on backups,** and write down that it passed.
- **Keep the restore verifier script in the repo and dry-run it in CI.**
- **Don't add backup or monitoring layers the platform already provides** for low-stakes projects; do add an off-platform monitor for anything users depend on (a monitor on the same server it watches dies with it).
