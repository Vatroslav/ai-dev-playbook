# deploy-static: first-time setup

Purpose: create `.claude/deploy.json` for a repo that has never been deployed with the skill, asking the human only what can't be derived.
Read when: the deploy-static skill finds no `.claude/deploy.json`.

## 1. Detect

- **versionFrom:** `package.json` with a `version` field; else `app/build.gradle.kts`; else `VERSION`; else `null` (then propose adding one; a deploy without a version can't be confirmed).
- **build / dist:** from `package.json` scripts and the framework config:

| Signal | build | dist |
|---|---|---|
| Vite (`vite.config.*`) | `npm run build` (with the repo's package manager) | `dist` |
| Next.js static export (`output: 'export'`) | `npm run build` | `out` |
| Create React App | `npm run build` | `build` |
| Astro | `npm run build` | `dist` |
| No bundler (plain HTML/JS) | `node scripts/build-dist.mjs` (copy it from the `new-web-app` skill's `templates/`) | `dist` |
| Single-file build produced elsewhere | `null` | the folder holding it |

- **target:** existing host config gives it away: `netlify.toml` -> netlify; `wrangler.toml` / `wrangler.jsonc` with `pages_build_output_dir` -> cloudflare-pages; a Pages workflow in `.github/workflows/` or a `CNAME` file -> github-pages.

## 2. Ask only what is left (one question per message)

1. The host, if step 1 didn't reveal it.
2. The project name on that host (itch slug, Netlify site, Cloudflare Pages project). Never derive it from the repo name; they often differ.
3. Who deploys. Propose: `agent` for a prototype or demo without real users, `human` for anything with real users. If the team picks `agent` for a product with users, ask them to record that decision in `docs/decisions.md`.

## 3. Validate the project exists

Use the "Exists" row for the target in [targets.md](targets.md). Not found: STOP. Hosts' CLIs often can't create projects; the human creates it in the host's UI. Tell them which settings to choose (for itch: Kind HTML, played in the browser, embed size matching the app's orientation, fullscreen button, mobile friendly).

## 4. Make the live version checkable

Unless the target reports versions itself (itch), the build must publish a version marker:
- No-bundler builds: `build-dist.mjs` already writes `dist/version.json`.
- Bundled builds: append a step to the build command, e.g. `"build": "vite build && node -e \"require('fs').writeFileSync('dist/version.json', JSON.stringify({version: require('./package.json').version}))\""`.
- Set `versionUrl` to `<liveUrl>/version.json`.

Showing the version in the app's UI as well (footer or settings) lets humans answer "which version are you on?".

## 5. Before the first public release

- **Store or landing material:** if the target has a public page (itch, app stores) and `promo/store/` is empty, offer the `store-page` skill.
- **Telemetry:** if the repo has none, tell the human in one sentence what is lost (the first days of usage can't be reconstructed later) and offer the `telemetry` skill. Continue on their answer; a "no" is a valid answer.

## 6. Write and commit the config

Write `.claude/deploy.json`, then `git commit -m "chore: add deploy config" -- .claude/deploy.json`. Continue with Step 1 of [SKILL.md](SKILL.md) in the same turn.
