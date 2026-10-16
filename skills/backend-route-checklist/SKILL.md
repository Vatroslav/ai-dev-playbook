---
name: backend-route-checklist
description: Checklist for adding or changing any server route, API handler, server action, middleware or data-layer function, or adding a public page. Use EVERY time an endpoint is added or modified, even a "trivial" one, and when reviewing route code ("add an endpoint", "new API route", "change the handler", "make this page public"). Skipping an item leads to a crash loop, a CSRF gap, a CSP gap on a new page, or shared data leaking into a bulk action. NOT for third-party API calls made BY the server (use api-client).
---

# Adding or changing a route

The request pipeline is layered on purpose. A route that ignores a layer works in dev and fails in production, quietly or loudly. Walk every item; most take seconds. Examples use Express; the same layers exist in Next.js route handlers/server actions, FastAPI and others - map them in "Project overrides".

## Preflight

- No server code touched (pure frontend, docs) -> `SKIP: no route or data-layer change`.
- The repo has no data layer (handlers query the DB directly) -> flag it as tech debt in the PR and still apply items 1, 3-7.

## 1. Async errors reach the error handler

Express 4 does not catch rejected promises from async handlers. Wrap every async handler:

```js
const ah = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
app.post("/api/items", ah(async (req, res) => { /* ... */ }));
```

Why: a single unwrapped handler turns every DB blip into an unhandled rejection that kills the process, and under a restart policy that becomes a container crash loop. There is no legitimate reason for an unwrapped async handler. The error handler returns a generic `{ "error": "internal error" }` - no stack traces, no SQL, no internals. (Express 5 and most modern frameworks forward rejections natively; check yours before assuming.)

## 2. Everything is scoped to the caller

- Handlers never touch the DB pool. Every DB access goes through a data-layer function whose FIRST parameter is the owner id and whose first line throws when it is missing:
  ```js
  function requireUser(userId) { if (userId == null) throw new Error("userId is required"); }
  async function listItems(userId) { requireUser(userId); return pool.query("select ... where owner_id = $1", [userId]); }
  ```
  Why: the driver binds `undefined` as NULL and the query silently matches nothing - or, with a different predicate, everything.
- Identity comes from one middleware (session, or a trusted auth-proxy header) that sets `req.userId` and fails closed (401) when it is missing. A "default dev user" variable is a local-only escape hatch, never set in production.
- Sharing pierces isolation deliberately: every new aggregate, count, bulk mutation or "all my items" query must decide explicitly whether shared items belong in it. Extend the isolation tests when you touch this boundary.
- Server actions (`"use server"`) are public HTTP endpoints: each one calls the guard itself.

## 3. Writes are JSON-only (CSRF layer)

Reject any non-GET/HEAD/OPTIONS API request without `Content-Type: application/json` (415). Form posts and bodyless fetches skip the CORS preflight, so without this a malicious page can fire writes with the victim's cookie (account delete, bulk clear). Companion layer: `SameSite=Lax` session cookie. Never exempt a route or accept form encoding "for convenience"; the client helper always sends JSON. (Frameworks with built-in CSRF tokens or origin checks: keep them on and test them.)

## 4. Middleware order and rate limits

Order is load-bearing:

`security headers -> body parser (size cap) -> CSRF guard -> public routes -> identity middleware -> per-user limiter -> authenticated routes -> error handler`

- Public (unauthenticated) endpoint: register it BEFORE the identity middleware, add it to the auth proxy's skip-auth list if you have one, and give it its own limits: per-IP plus a global backstop. The backstop still holds if IP attribution is wrong behind proxies; per-IP needs the trusted-proxy hop count set in production, otherwise every visitor shares one bucket and real users get locked out.
- Authenticated route: after the identity middleware; inherits the limiter keyed on user id.

## 5. New public page

Check all of these:
1. The CSP: pages that render user data keep a strict `script-src 'self'` with no inline handlers; only static marketing pages may get a relaxed policy.
2. The auth proxy's skip-auth list (or the framework's public-route matcher).
3. Whether static serving also exposes `/<name>.html` next to the pretty URL - 301 it to the canonical URL.
4. Assets the page needs (favicon, fonts, CSS) are reachable logged-out.
5. API routes that return HTML or SVG: confirm the CSP actually applies to them (middleware matchers often exclude `/api/*`).

## 6. Input bounds, response shape, outbound HTTP

- Per-field caps on everything a user submits (length, count, numeric range); the JSON body-size limit is only the outer net.
- Mutating routes return the full updated state, so the client re-renders from one source of truth instead of patching local state.
- Outbound HTTP only through the SSRF-guarded fetcher (scheme allowlist, IP-literal and resolved-address checks, redirect re-validation, deadline, byte cap) and, for background work, through the concurrency limiter. Never a bare `fetch(userSuppliedUrl)` in a handler. Details: `docs/agent/security.md`.
- Destructive actions: confirmation step or soft delete with a recovery window; where the client can't confirm, send the expected entity id and return 409 if it changed.

## 7. Test and version

- Every route or data change gets a test that drives the real app over HTTP on the in-memory DB harness, with counter-test evidence (the test fails without the fix). See verify-without-infra.
- Guard tests (CSRF, scoping, CSP) include a positive control: legitimate traffic still passes.
- Bump the version by intent (`feat` minor, `fix`/`perf` patch) in the same commit.

## Output

In the PR body, a "Route checklist" line per item: `1 async ok | 2 scoped via data.listItems | 3 JSON-only ok | 4 public, limits added | 5 n/a | 6 caps added | 7 test/routes-items.test.js`.

## What NOT to do

- No handler that queries the pool directly.
- No route exempted from the CSRF guard.
- No public route registered after the identity middleware "because it works locally".

## Project overrides (fill in)

- Framework and where each layer lives: `<e.g. Next.js: middleware.ts = headers + auth matcher; server actions call requireUser()>`
- Identity source: `<session cookie | X-Forwarded-Email from the auth proxy>`
- Auth proxy skip-list file: `<path or n/a>`
- Rate limiter config: `<path>`
- SSRF-guarded fetcher: `<src/lib/safe-fetch.ts>`
