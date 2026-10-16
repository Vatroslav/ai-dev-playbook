---
name: new-web-app
description: Playbook for building a small web app, PWA or clickable prototype from scratch - from a few sentences and reference screenshots to an installable app that is live on a public URL, then improved through a measure-then-fix loop. Use on "/new-web-app", "build me an app like this", "make a quick prototype of X", "spin up a landing/demo app", or screenshots of a simple app with a request to make one. Use it even when the request looks tiny - skipped verification is the main failure mode. NOT for adding a feature to an existing product repo.
---

# New web app

Purpose: get from idea to a live, usable app quickly without the usual prototype failures - an agent asking the human to pick technologies, "done" declared from code that was never opened in a browser, and a deploy that is green while the app is dead.

## Preflight

- No idea description and no reference: print `SKIP: describe the app in a few sentences or attach reference screenshots` and stop.
- The request is a feature for an existing product: print `SKIP: this is a feature, not a new app - work in the product repo` and stop.

## 0. Division of labour

- **The product owner** gives the idea and references, owns product questions (name, features, user-facing copy, what the app must never do), and later reports bugs and what feels right. They don't choose technology.
- **The agent** decides everything technical: language, file layout, structure, palette, effects. No option menus. Why: a menu of technical options hands work to someone who can't judge it; it doesn't give them control.
- Ask only what can't be derived, ONE question per message. Typical: "Is this mainly for phones?" (default: mobile-first PWA; desktop gets a centred max-width column).
- Collect all product questions in one round before building, when changes are cheapest. Mark anything you invented (categories, names, rules) as a working proposal until the owner rules on it.
- Dark patterns in the reference (nagging, fake urgency, hidden prices, ads) are not features to copy. Often they are the reason the new app should exist.

## 1. Repo and session

- New repo with a short English name that can double as the URL slug. Private by default; public only when hosting requires it (GitHub Pages on a free plan) or the team decides so.
- Point the agent session at the new repo before writing code.
- Write AGENTS.md immediately (start from the playbook's AGENTS.md): what the app is for, principles (no tracking, accounts or network calls unless decided), where things live, how to run it locally, how deploy works.
- Run the `setup` skill (linting + version guard). For a throwaway prototype the version guard may wait until it proves it will live on.

## 2. Technical standard

Pick the lightest stack that fits; record the choice and the reason in `docs/decisions.md`.

- **Single-purpose utility or prototype:** vanilla JS, no build step, no framework, no dependencies. Classic `<script>` tags with one global namespace per module (`App.logic`, `App.ui`), not ES modules. Why: it works over `file://`, the service worker stays trivial, and every dependency becomes an explicit decision.
- **Needs routing, accounts, a backend or shared state:** the team's standard stack (for example Vite + TypeScript, or Next.js). Strict TypeScript, no `any` without a comment saying why.

Rules for both:
- **Business logic never touches the DOM**, so it runs in plain Node: `node -e "eval(require('fs').readFileSync('logic.js','utf8')); console.log(App.logic.check(/*...*/))"`, or for TS `npx esbuild src/logic.ts --bundle --platform=node --format=esm --outfile=/tmp/logic.mjs && node /tmp/logic.mjs`. Keep scratch test files outside `src/` (a stray `.js` next to a `.ts` can be served instead of it).
- **Mobile basics:** `viewport-fit=cover`, `theme-color`, an apple-touch icon; CSS `100dvh`, `env(safe-area-inset-*)`, `touch-action: manipulation`. Size layouts from the viewport (compute the largest size that fits width AND height, write it into CSS variables, or scale one design resolution by a single factor). No fixed-pixel caps, no per-device constants.
- **Relative asset paths** (`base: './'` in Vite). Why: apps served from a subfolder or an iframe otherwise load as a white screen.
- **Service worker: network-first, bypassing the HTTP cache**, cache only as offline fallback. Copy `templates/sw.js`. The cache name is internal, not the app version, so it never needs a bump.
- **One source of truth for the version** (`package.json`), injected at build time or fetched at runtime, and shown in the UI (settings or footer). Why: "which version are you on?" must have an answer for every bug report.
- **Every `JSON.parse` of localStorage is wrapped in try/catch.** Persist user state and settings. A corrupted entry must never crash the app.
- **Results you can't prove are not shown as facts.** A function that may give up (search limit, timeout) returns three states: a result, "proven none", or "unknown". Show "nothing found / impossible" only on proof. Error and empty states always offer a way out (undo, retry, back).
- **Generated or computed content gets an independent check** that shares no code with the generator, and names the exact failing case. Seed generated content by its index so item N is always the same; changing the generator is a breaking change - tell the owner.
- **First run:** one short hint explaining the core action, remembered after it was shown.
- **Dev-only test toggles** via URL query (`?step=5`, `?seed=42`), inactive in production builds and logged to the console when active, so the human and the agent can jump straight to the state under test.
- **Colours live in one palette file**; no colour literal anywhere else (check with grep). When colours must stay distinguishable (charts, categories, status), run `python scripts/palette-check.py "#hex1" "#hex2" ...` (next to this skill) after every palette change: it prints the closest pair for every prefix, because early screens use the first N colours.
- **Feel is optional but cheap:** short CSS transitions, `navigator.vibrate` in try/catch, sounds synthesised with WebAudio (no audio files) behind a persisted mute toggle. Resume the AudioContext on the first user gesture, or the app stays silent.

## 3. Local preview

Register the dev server so the agent's preview browser can open it (`.claude/launch.json` in Claude Code):

```json
{ "version": "0.0.1", "configurations": [
  { "name": "static", "runtimeExecutable": "python", "runtimeArgs": ["-m", "http.server", "8123"], "port": 8123 },
  { "name": "dev", "runtimeExecutable": "npm", "runtimeArgs": ["run", "dev"], "port": 5173 }
] }
```

Make the dev server honour a `PORT` environment variable (Vite: `server.port: Number(process.env.PORT) || undefined`). Why: preview tools assign ports, and a hardcoded port can silently show another project's server running on it. If the preview shows code without your change, check the port owner before debugging code.

When the human wants to try something, start the server yourself and give one link with the dev toggles already set for that feature.

## 4. Before saying "done"

Never ship on "the code looks right". In the browser:

- [ ] Walk the main flow end to end: reach success, reach a failure or empty state, press every button.
- [ ] Reload in the middle of a session: progress and settings come back.
- [ ] Console clean; network tab without 404s or failed requests.
- [ ] Mobile viewport preset, then reload. Also check a desktop width.
- [ ] Measure invariants in Node instead of estimating them (e.g. generate the first 30 items and run the independent checker). Put the numbers in the commit message.
- [ ] Before a public launch, open it once in Firefox and Safari (the engines that differ from Chromium).
- [ ] Screenshots of canvas-heavy pages can hang in background tabs; verify numerically (computed styles, element counts) and tell the human the visual judgement is still theirs.

## 5. Ship

- GitHub Pages from `main` (static, no build): `gh api -X POST repos/<owner>/<repo>/pages -f "source[branch]=main" -f "source[path]=/"`. On a free plan this needs a public repo.
- Any other static host: use the `deploy-static` skill.
- Verify it is actually live; don't assume: `curl -sI https://<owner>.github.io/<repo>/ | head -1`, then check that the live page carries the new version. Hosts can serve stale files for minutes; hard-reload before concluding anything.
- Telemetry is off by default. If the owner wants usage numbers, run the `telemetry` skill **before** the first public release: the first days can't be reconstructed later.
- In the README: why the app exists (which frustration it removes), how it is built, how to run it, and an empty "Feedback and bugs" section.

## 6. After shipping: measure first, then fix

1. For each report, write down the user's words verbatim.
2. Before reading code for the bug, write a small script that turns the report into numbers over real data (e.g. "the import sometimes skips rows" becomes "% of files with skipped rows, grouped by delimiter and encoding").
3. Fix, then put the measured numbers and the reasoning in the commit message: `git log` becomes the app's decision history.
4. Re-run the "before saying done" checklist, bump the version per its intent, deploy, confirm the live version.
5. Record the finding and the outcome under "Feedback and bugs".

## What NOT to do

- Don't offer the human a choice of frameworks or libraries.
- Don't add accounts, analytics, ads or network calls that weren't decided.
- Don't change the core of a template while building an app from it; if the template needs a change, fix the template.
- Don't move past a milestone the owner hasn't tried and approved.

## Output (final message)

```
<App name> v<version> is live: <URL>
Verified: <checklist items done, with numbers>
Not verified: <what still needs a human eye, e.g. feel, real devices>
Decisions taken by the agent: <one line each>
Open product questions: <list or "none">
```
