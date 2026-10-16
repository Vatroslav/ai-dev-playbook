# deploy-static: per-target commands

Purpose: the exact check, push and confirm commands per host, so the main skill stays generic.
Read when: the deploy-static skill reaches a step that says "per target".

Placeholders: `<dist>`, `<version>` and the target block values come from `.claude/deploy.json`. CLI flags change between releases: if a command fails on an unknown flag, check `<cli> <command> --help` before improvising.

## itch (HTML5 games and web toys)

Config block: `"itch": { "project": "<user>/<slug>", "channel": "html5" }`. The slug is the one in the itch.io URL, not the repo name. Channel `html5` for browser builds, or `windows` / `osx` / `linux` for downloads.

| Step | Command / rule |
|---|---|
| Check | `butler version`. Missing: install butler from itch.io's official download page (unpack all files of the archive into a folder on PATH). |
| Login | `butler login`, run by the human (browser OAuth). Login is per user, not per project. |
| Exists | `butler status <project>:<channel>`. "Not found": butler cannot create projects. The human creates it on itch.io (Kind = HTML, "played in the browser" ticked, embed size matching the app's orientation, fullscreen button on, mobile friendly if it works on phones). |
| PREV | `butler --json status "<project>:<channel>" 2>/dev/null \| grep '"type":"result"' \| node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{console.log(JSON.parse(s).value.channels[0].head.userVersion)}catch{console.log("")}})'` |
| Push | `butler push <dist> "<project>:<channel>" --userversion "<version>"` |
| Confirm | `butler status "<project>:<channel>"`: the build is processed and shows `<version>`. Then open the page and play it in the embed. |

- Read PREV from `--json` output: plain `butler status` also prints butler's own "new version available" banner, which a version regex catches instead.
- `--userversion` keeps the itch build label equal to the in-app version.
- Keep a new page in Draft until the first build is pushed and tested in the embed (loads, right orientation, controls work), then let the owner make it public.

## netlify

Config block: `"netlify": { "site": "<site name or ID>" }`.

| Step | Command / rule |
|---|---|
| Check | `npx netlify --version` |
| Login | `npx netlify login`, run by the human. `npx netlify status` shows the account. |
| PREV | `curl -fsSL "<versionUrl>?cb=$(date +%s)"` |
| Push | Draft first: `npx netlify deploy --dir=<dist> --site=<site>` prints a draft URL; check it. Then production: `npx netlify deploy --dir=<dist> --prod --site=<site>`. |
| Confirm | Poll `versionUrl` (SKILL.md Step 5). |

## cloudflare-pages

Config block: `"cloudflarePages": { "project": "<project name>", "branch": "main" }` (`branch` = the project's production branch; any other branch name creates a preview deployment).

| Step | Command / rule |
|---|---|
| Check | `npx wrangler --version` |
| Login | `npx wrangler login`, run by the human. `npx wrangler whoami` shows the account. |
| Exists | `npx wrangler pages project list` |
| PREV | `curl -fsSL "<versionUrl>?cb=$(date +%s)"` |
| Push | `npx wrangler pages deploy <dist> --project-name=<project> --branch=<branch>` |
| Confirm | Poll `versionUrl`. |

## github-pages

No target block needed. The deploy is the push to the publishing branch (branch source) or the Pages workflow run (Actions source); this skill does not push.

| Step | Command / rule |
|---|---|
| Check | `gh auth status` |
| Exists | `gh api repos/<owner>/<repo>/pages --jq .html_url`. 404: Pages is not enabled. Enable from `main`: `gh api -X POST repos/<owner>/<repo>/pages -f "source[branch]=main" -f "source[path]=/"`. A free plan needs a public repo. |
| PREV | `curl -fsSL "<versionUrl>?cb=$(date +%s)"` before the push. |
| Build status | Branch source: `gh api repos/<owner>/<repo>/pages/builds/latest --jq .status` (wait for `built`). Actions source: `gh run list --limit 1` on the Pages workflow. |
| Confirm | `curl -sI <liveUrl> \| head -1`, then poll `versionUrl`. Pages can serve stale files for minutes; hard-reload in the browser before concluding anything. |

## command (any other host)

Config block: `"command": { "check": "<command that proves the tool works and is logged in>", "push": "<push command with {dist} and {version} placeholders>" }`.

Example: `"push": "rsync -az --delete {dist}/ deploy@static.example.com:/var/www/app/"`.

- Substitute the placeholders, print the final command, then run it (or hand it off when `whoDeploys` is `human`).
- `versionUrl` is mandatory for this target: without it there is no proof the deploy landed.
