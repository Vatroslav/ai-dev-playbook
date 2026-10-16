---
name: telemetry
description: Set up anonymous product telemetry for the app in the current repo - a small agreed event set, a client that can never hurt the app, one isolated collector (own backend table, or a free Google Sheet + Apps Script option), a health endpoint and an aggregates-only dashboard that filters out dev traffic and the team's own sessions. Use on "/telemetry", "set up telemetry", "add usage metrics", "how many people use this", or when deploy-static's first-time setup offers it before a first public release. NOT for error monitoring or crash reporting, and NOT for analysing data that already exists.
argument-hint: "[optional: own-backend | sheets]"
---

# Telemetry

Purpose: answer product questions ("do people finish the main task? where do they drop off? do they come back?") with numbers, without collecting personal data and without any risk to the app. Do it BEFORE the first public release: the first days can't be reconstructed later.

## The pattern (applies to every collector option)

- **Every event maps to a decision it could change.** If nobody can say what they would do differently based on a number, don't collect it.
- **No PII, ever:** no names, emails, user ids, free text, IP-derived location, URLs with query strings. The only identifier is an anonymous random id per device.
- **The client never hurts the app:** everything in try/catch, fire-and-forget, `keepalive: true`, an empty endpoint means a deliberate no-op. A broken collector must be invisible to users.
- **`env` is detected, not configured:** `dev` on a local host or `file://`, `prod` everywhere else. Never keep a list of production hosts: hosts, embeds and CDNs change domains and the list silently breaks.
- **Contract columns, found by name:** `ts, session, version, env, event, payload, client_ts`. App-specific fields go into `payload` (a JSON string or column); promoted columns are added strictly at the end. Why: a new metric needs no schema change, and inserting a column in the middle shifts existing rows.
- **One isolated collector per app.** Why: one app can't break another app's telemetry or mix different measures into one table.
- **A public dashboard returns aggregates only**, always filters `env = 'prod'`, and filters the team's own sessions through a list of ids kept as data (a table or a tab), not code. Why: in a small launch, a handful of the team's own test sessions is a large share of all sessions, enough to change the conclusion.
- **Days before an event existed are null, missing days are 0.** "Not measured" is not "zero", and a skipped day makes a dead week look like traffic.
- **A session is a device, not a person.** Count per use (one id per attempt), not per session; read the trend, never the absolute "number of people".
- **A health endpoint returns counts only** (rows, last event, per-event tally, timezones). Check it first whenever numbers look wrong.
- **Consent:** check whether your jurisdiction requires consent for storing an identifier on the device for analytics (in the EU, ePrivacy rules can apply even without personal data). If unsure, ask the product owner before launch, or drop the persistent id and count uses only.

## Preflight

- No app code in the repo: print `SKIP: no app to instrument` and stop.
- The app's principles say "no tracking" (AGENTS.md or README) and there is no recorded decision to change that: print `SKIP: the repo forbids tracking - record a decision in docs/decisions.md first` and stop.

## Step 0: Detect state (re-runnable)

Continue from the first missing piece: client file present? endpoint set (non-empty)? collector exists (own-backend table or `metrics/apps-script/.clasp.json`)? dashboard exists? `metrics/README.md` exists? Also collect the app name, its public URL (from `.claude/deploy.json` or README) and whether it has a backend with a database.

## Step 1: Propose the events (the product owner confirms)

Propose, don't ask open questions. Base set:

| Event | When | Answers |
|---|---|---|
| `app_opened` | app loaded | denominator; the only trace of returning devices |
| `<x>_started` | the core action really began (not on page load, not in a constructor) | how many attempts |
| `<x>_finished` | the core action completed | completion rate |
| `<x>_left` | `pagehide` during an attempt (not `visibilitychange`: a hidden tab is a pause) | WHERE people abandon, not just that they did |

Use the team's own words for `<x>` and keep the same term in code, docs and events. Add a payload field only if it changes a decision (step reached, duration, result). Then ask one yes/no question: "Filter out the team's own devices?" (default yes for a team, since teammates test constantly).

## Step 2: Pick the collector

- **Own backend (default when the app already has a server and a database):** a `telemetry_events` table and a `POST /api/events` route. Schema and dashboard queries: [templates/events.sql](templates/events.sql). The route parses the `text/plain` body as JSON, accepts only events from an allowlist, caps the payload size (for example 2 KB), rate-limits per IP without storing the IP, writes the row with server time, and returns 204. A `GET /api/events/health` route returns counts only. Apply the team's route checklist (see [engineering notes](../../docs/agent/engineering-notes.md)).
- **Google Sheet + Apps Script (free, serverless, for static apps without a backend):** follow [sheets-option.md](sheets-option.md).
- **A hosted analytics product** is fine if the team prefers one; the pattern rules above still apply. Out of scope for this skill.

## Step 3: Client

Copy [templates/metrics.js](templates/metrics.js) and load it before the app code. Set `ENDPOINT` (own backend: `/api/events`; Sheets: the collector's `/exec` URL), a unique `SID_KEY`, and `PROD_KEYS` (the payload keys allowed in prod). Call `Metrics.track("<x>_started", { ... })` at the real moments from Step 1. For TypeScript apps, wrap it in a typed `track()` with an event-name union.

Optional: a dev-only local collector (the dev server appends full payloads to a gitignored JSONL file) for calibrating while the team tries the app; the hosted collector keeps the narrowed payload.

## Step 4: Verify the whole chain

1. Probe from the command line with `env: "dev"` (never fake prod rows):
   `curl -s -L -X POST -H "Content-Type: text/plain" -d '{"session":"probe-cli","env":"dev","event":"probe","payload":{},"ts":0}' "<endpoint>"`
2. The health endpoint shows one more row and `probe` in the tally.
3. A teammate uses the app locally: a real event with `env: "dev"` appears.
4. Push a deliberately broken endpoint URL locally and check the app still works with a clean console.

## Step 5: Dashboard

Aggregates only, `env = 'prod'`, own sessions excluded, null before first appearance, zero-filled days, KPIs labelled honestly ("devices", "active days"). Own backend: the queries in `events.sql` behind an authenticated admin page or a scheduled export. Sheets: `dashboard.js` + `Index.html` (see [sheets-option.md](sheets-option.md)).

## Step 6: Record

`metrics/README.md`: collector type, endpoint and dashboard URLs (no secrets), the event table with the decision each event serves, where the own-session list lives, how to check health. One line in AGENTS.md pointing to it. Commit with explicit paths (`feat:` if the client ships in the app, so the version guard asks for a bump).

## Traps

- Events missing: check health first; then: is the endpoint set in the shipped build? Are the rows `dev` while the dashboard counts only `prod`? Is the client using `text/plain`?
- Numbers jump after launch day: the team's own devices are not in the own-session list yet.
- Daily charts shifted by one day: the store's timezone differs from the server's. Show both in the health output; when auditing compare UTC offsets, not zone names.
- "Started" counts equal page loads: the event fires on load or in a constructor instead of when the action really begins.

## Boundaries

- Never sends one app's events to another app's collector.
- Never stores PII, free text or raw IPs; never exposes rows publicly.
- Test events only with `env: "dev"`.
- Doesn't add tracking to a repo whose principles forbid it without a recorded decision.
- Doesn't deploy the app; the client ships with the next normal deploy.

## Output

```
Telemetry
- Collector:  <own backend table + route | Sheets project> (health: <ok, N rows>)
- Events:     <list, each with the decision it serves>
- Client:     <file>, endpoint <set | empty = off>, prod payload keys <list | full>
- Dashboard:  <URL or page> (aggregates only, prod only, own sessions <filtered | not filtered>)
- Verified:   probe row <ok>, local real event <ok>, broken endpoint harmless <ok>
- Not done:   <e.g. consent check pending with the product owner>
```
