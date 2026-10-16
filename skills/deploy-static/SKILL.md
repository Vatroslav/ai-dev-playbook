---
name: deploy-static
description: Build and push a static web build (SPA, PWA, HTML5 game, docs site) to a static host - itch.io, Netlify, Cloudflare Pages, GitHub Pages or a custom command - then confirm the live version. Reads a per-repo config (.claude/deploy.json); without one it runs a one-time setup. Use on "/deploy-static", "deploy the build", "push it live", "publish a new build". NOT for servers, containers or databases (see docs/agent/ci-cd-and-deploy.md), and NOT for bumping versions or tagging releases.
disable-model-invocation: true
argument-hint: "[optional: dry-run]"
---

# Deploy a static build

The procedure lives here and is the same for every repo; the specifics live in each repo's `.claude/deploy.json`. Never branch this skill by project name: if a repo needs something different, extend the config schema. Follow the steps exactly; don't improvise.

Why the steps are strict: a green build plus a green deploy can still be a dead product (a missing build-time environment variable, for example, passes the build and the deploy and breaks the app for every user). Only a check of the live site proves a deploy.

## Config: `.claude/deploy.json`

```json
{
  "target": "netlify",
  "whoDeploys": "agent",
  "build": "npm run build",
  "dist": "dist",
  "versionFrom": "package.json",
  "liveUrl": "https://my-app.netlify.app/",
  "versionUrl": "https://my-app.netlify.app/version.json",
  "netlify": { "site": "my-app" }
}
```

| Field | Meaning |
|---|---|
| `target` | `itch`, `netlify`, `cloudflare-pages`, `github-pages` or `command`. Per-target commands: [targets.md](targets.md). |
| `whoDeploys` | `agent` or `human`. `agent` only for prototypes and demos without real users, or where the team recorded that decision in `docs/decisions.md`. A product with real users is `human`: agents have no production access (see AGENTS.md). |
| `build` | Command that produces `dist`, or `null` when the build is produced elsewhere. |
| `dist` | Folder that gets pushed. |
| `versionFrom` | `package.json`, `app/build.gradle.kts` (`versionName`), `VERSION`, or `null`. |
| `liveUrl` | The page users open. |
| `versionUrl` | A URL whose body contains the live version (usually `<liveUrl>/version.json`). `null` only when the target reports versions itself (itch). |
| target block | `itch: {project, channel}`, `netlify: {site}`, `cloudflarePages: {project, branch}`, `command: {check, push}`. |

No config: run [first-time.md](first-time.md), then continue with Step 1 in the same turn.

## Step 1: Preconditions (check, don't assume)

- The host CLI works and is logged in (check command per target in [targets.md](targets.md)). Login is done by a human in their browser. Never open or print the CLI's credential files.
- Read the version: `node -p "require('./package.json').version"` (or the file in `versionFrom`). Unclear source: ask, don't guess.
- `git status --porcelain` shows uncommitted source changes: WARN that the build is not what is in git. Don't block.
- Argument `dry-run`: do Steps 2-3, print the push command, stop.

## Step 2: Build and inspect

1. `build` set: run it. It must pass cleanly. On failure STOP and report; never push a broken or partial build.
2. `build` is null: `dist` must exist and be non-empty, otherwise STOP and ask for a build.
3. Inspect the output before it leaves the machine:
   - `find <dist> -name ".env*" -o -name "*.pem" -o -name "*.key"` returns anything: STOP. Secrets must never ship.
   - `grep -nE '(src|href)="/[^/]' <dist>/index.html` finds root-absolute asset paths: STOP for hosts that serve from a subfolder or iframe (itch, GitHub Pages project sites), warn otherwise. Why: the result is a white screen (fix: relative base, e.g. Vite `base: './'`).
   - The version marker exists if `versionUrl` points into `dist` (e.g. `<dist>/version.json` contains the version).

## Step 3: Read the version that is live now

`PREV` = the version before this deploy (command per target in [targets.md](targets.md); for most targets `curl -fsSL "<versionUrl>?cb=$(date +%s)"`). Empty is fine on the first deploy. PREV is the boundary for the release-notes draft.

## Step 4: Push

- `whoDeploys: agent`: run the push command from [targets.md](targets.md).
- `whoDeploys: human`: print a hand-off block and wait for "done". It says where it runs (local terminal), as which account (the host account the CLI is logged in with), in which folder; `cd` is the first line inside the block; the literal push command follows. Add one sentence on what it does and that it replaces the live site. Don't print a rollback command unless asked: people run code blocks in order.
- `github-pages`: the deploy is the normal push to the publishing branch (or its workflow). This skill doesn't push git; it confirms after the push.

## Step 5: Confirm it is live

1. Poll the live version with a cache-buster; hosts and CDNs can serve stale files for minutes:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -fsSL "<versionUrl>?cb=$(date +%s)" | grep -qF "<version>" && { echo "live: <version>"; break; }
  sleep 15
done
```

   (itch: `butler status` instead, see [targets.md](targets.md).) Still old after the loop: report it as NOT confirmed. Don't declare success.
2. Smoke-check the main flow on `liveUrl`, not only your change: open it in the preview browser (or `curl -fsS <liveUrl>` and grep for an element only the new build has), walk the main flow once, console clean. Why: the deploy can be live and the product still broken.
3. Live but behaving like the old version: first prove what is served (curl the page, grep for a new symbol) and check you are not looking at another session's local server, before debugging logic.

## Step 6: Report

```
Deployed <app> v<version> (was <PREV or "nothing">) to <target>
Live URL: <liveUrl>
Version check: <confirmed after N tries | NOT confirmed: what was served>
Main flow: <checked: what | not checked: why>
Build: <command>, <file count / size of dist>
Warnings: <dirty tree, absolute paths, ... | none>
```

## Step 7: Release-notes draft (optional)

Tiny patches need none; say so. Otherwise:
1. Boundary = the commit where the version file became PREV: `git log --reverse --format=%H -S '"version": "<PREV>"' -- package.json | head -1`.
2. Commits since: `git log --no-merges --format=%s <boundary>..HEAD`.
3. Draft in plain user language: strip commit prefixes and jargon, merge related changes, drop internal-only work. Classify as Major (real news) or General (roundup). Title in inline code; body as a short list (HTML fragment if the target page uses HTML).
4. Print it in chat. Never publish it: posting is the product owner's call.

## Boundaries

- Does not bump the version (the commit guard enforces that), commit, tag or `git push`.
- Does not change host settings: visibility, pricing, domains, environment variables, page layout, embed options. Those are the owner's call in the host's UI.
- Does not publish release notes or store text.
- Never reads, prints or copies host credentials or tokens.
- Never deploys over a failed build or an unconfirmed inspection.
