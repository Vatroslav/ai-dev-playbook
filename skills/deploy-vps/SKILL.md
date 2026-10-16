---
name: deploy-vps
description: Deploy an app that runs on a single VPS with Docker Compose (git pull + docker compose up --build over SSH) and verify it actually booted - container state, app log, health endpoint, deployed SHA. Use when someone says "deploy to the server", "update the VPS", "push it to the box", for a project whose Project overrides below are filled in. For production the agent prepares the commands and a human runs them. NOT for tagging a release (use release), NOT for static hosting (use deploy-static) or PaaS (see docs/agent/ci-cd-and-deploy.md).
disable-model-invocation: true
argument-hint: "[environment: staging|production]"
---

# Deploy to a VPS (Docker Compose)

Follow these steps exactly - do not improvise alternative paths.

Why: compose prints "Started" for a container that dies a second later, the test suite never builds the image, and `restart` silently ignores `.env` changes. Each step below catches one of those before a dead deploy can pass as green.

## Preflight

- Project overrides below still contain `<placeholders>` -> `SKIP: deploy target not configured - fill in Project overrides (real host values go in a gitignored local file, never in this skill)`.
- The commit to deploy is not on `origin/main` -> push/merge first. Deploy released commits on `main` only.
- Target environment is production -> **handoff mode** (default for production; see `docs/agent/security.md`): the agent prints each command block for a human and runs nothing that changes the server.
- Target environment is listed under "Agent may deploy to" -> **agent mode**: the agent runs the commands itself.

## Placeholders

Real values live in a gitignored local file (e.g. `.deploy.local`) or private notes, never in this committed skill:
- `$DEPLOY_USER`, `$DEPLOY_HOST` - SSH target
- `$DEPLOY_REPO` - path of the git clone on the server
- `<port>` - the app's internal port

## Server layout (expected)

- Full clone at `$DEPLOY_REPO`; compose file in the repo.
- `.env` on the server, created once from `.env.example`, never committed. Humans type secret values into it from their own shell; the agent may scaffold non-secret keys only.
- Services: `db` with a healthcheck (`app` has `depends_on: { db: { condition: service_healthy } }`), `app` on an internal port, reverse proxy for TLS; internal services bound to `127.0.0.1`.
- Data in a named volume. The compose project is pinned with a top-level `name:` so the volume name never depends on the directory you run from.
- Backups: provider snapshots plus a restore drill that has actually passed.

## Steps

1. **Confirm what will be deployed.** `git log origin/main --oneline -1` and the version in the version file. State both.

2. **Env check** (before every `up`): required keys present on the server, by NAME only - never print values:
   ```bash
   ssh $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_REPO && grep -oE '^[A-Z_]+=' .env | sort"
   ```
   Typical traps: the trusted-proxy hop count is missing (every visitor then shares one per-IP rate-limit bucket and real users get locked out); an auth or session secret that is missing or in the wrong format; an access restriction meant for testing left on in production.

3. **Deploy** (one command, timeout 120 s or more):
   ```bash
   ssh $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_REPO && git fetch origin && git checkout main && git merge --ff-only origin/main && docker compose up -d --build"
   ```

4. **Boot verification (MANDATORY - do not trust "Started").**
   ```bash
   ssh $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_REPO && docker compose ps"                 # no service "Restarting"
   ssh $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_REPO && docker compose logs --tail 30 app" # listening line, no stack trace
   ```
   `Cannot find module` / `ModuleNotFoundError` = the image is missing a file (e.g. `COPY *.js` matches top-level files only; modules in subfolders need their own COPY).

5. **Health check.**
   ```bash
   ssh $DEPLOY_USER@$DEPLOY_HOST "curl -s http://localhost:<port>/health"                      # 200; version == repo version; workers alive
   ssh $DEPLOY_USER@$DEPLOY_HOST "curl -s -o /dev/null -w '%{http_code}\n' http://localhost:<port>/"
   ssh $DEPLOY_USER@$DEPLOY_HOST "cd $DEPLOY_REPO && git rev-parse --short HEAD"
   ```
   Then check the product's main user flow from outside (public URL), not just your change.

6. **Report** (format below).

### Env-only change
Edit `.env` on the server (human, for secrets), then `docker compose up -d --force-recreate` - `restart` does NOT re-read `.env`. Run steps 4-5.

## Handoff mode (production)

Print each block in the format from `docs/agent/collaboration.md`: where it runs (local terminal with SSH access), as which account, in which folder (`cd` as the first line inside the block), what it does, risk. One block per step. Ask the human to paste the output of steps 4-5 back, then evaluate it. Do not print a rollback command unless asked - people run code blocks in order.

## Output

```
Deployed <env>: vX.Y.Z (commit abc1234 on server, == origin/main)
Boot: all services Up, app log shows "listening on <port>", no errors
Health: /health 200 {version: X.Y.Z, workers: ok}; / 200; main flow checked: <what>
```
On failure: the exact failing command, its output, and the matching troubleshooting line.

## Troubleshooting

- App restarting: read the app log. DB connection refused: `docker compose logs db` (a failing DB healthcheck blocks the app).
- Auth proxy restarting: read its log; usually a missing or malformed client credential or secret.
- Login rejected (403 after login, or new users can't sign in): check the proxy's allowlist and the OAuth app's publishing status.
- TLS issuance fails: make sure the HTTP-01 challenge reaches the server and nothing in front of it intercepts the request (or switch to DNS-01).
- Container-name conflict or suddenly empty data: the compose project name changed and a new empty volume was created. Restore `name:`; never keep the second volume.

## What NOT to do

- No improvised paths (rsync, manual `docker run`, editing files on the server).
- No deploys of branches or unpushed commits to production.
- No reading or printing `.env` values; no secrets in commands or chat.
- No `docker compose down -v` (it deletes volumes) without an explicit human decision.

## Project overrides (fill in)

- Agent may deploy to: `<staging only | none>`
- Compose file path: `<docker-compose.yml>`
- App service name and internal port: `<app>` `<3000>`
- Health path: `</health>` (returns version and worker liveness)
- Public URL for the main-flow check: `<https://...>`
