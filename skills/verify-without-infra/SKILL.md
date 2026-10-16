---
name: verify-without-infra
description: Test and verify backend changes with zero infrastructure - real HTTP against the app on an ephemeral port, the production SQL against an in-memory Postgres (pg-mem) or a temp SQLite file, the counter-test discipline for fixes, and a browser preview of the UI without a database. Use whenever writing or changing tests, proving a fix works, previewing UI changes, or smoke-testing the server locally ("write a test for", "verify the fix", "preview this", "there's no local DB"). Never skip verification because "there is no database", and never point a test at a real one.
---

# Verifying without infrastructure

The suite runs the real production query path (same SQL, `$1` placeholders, transactions) against an in-memory engine, and drives the real app over HTTP. The same trick boots the full app for a browser preview. Reuse the harness; don't reinvent it.

Why: "no local database" is the most common excuse for unverified backend changes, and tests against a shared or real database are how test runs end up changing real rows.

## Preflight

- No test runner configured -> for Node, `node --test` needs nothing (Node 18+); add `"test": "node --test"` to `package.json`. For Python, add pytest as a dev dependency (ask first if the repo has no dev dependencies).
- The app module opens a DB connection or calls `listen()` on import -> fix that first (export the app; listen only when run directly; data layer accepts `init(poolOverride)`). Without it nothing below works.

## Test skeleton (Node: node:test + pg-mem)

`test/pgmem.js` is next to this file (copy it into your `test/` folder; `npm i -D pg-mem`).

```js
// test/items.test.js
// Why this file exists: <which finding, attack or incident it guards against>
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { memPool } = require("./pgmem"); // fresh isolated in-memory DB per call
const app = require("../server");        // requiring the app must not open a DB or listen
const data = require("../data");

let server, base;
test.before(async () => {
  await data.init(memPool());            // data layer accepts a pool override
  server = http.createServer(app);
  await new Promise((r) => server.listen(0, "127.0.0.1", r)); // port 0 = any free port
  base = `http://127.0.0.1:${server.address().port}`;
});
test.after(async () => {
  await new Promise((r) => server.close(r));
  await data.close();
});
```

- Identity: send the same header or cookie your production auth layer sets, on every request, so the identity and scoping path is exercised. Different identities = different users (that is how isolation is tested).
- Seed through the API, not by writing to the DB. The API is the contract under test.
- Start every test file with a comment saying WHY it exists.
- Use small raw `http.request` helpers where you need attack shapes (form-encoded bodies, bodyless POSTs) that a JSON helper can't produce.
- Stubbing globals (`Date.now`) always sits in `try/finally`.

More patterns (fault injection, multi-tenant leak guard, CSRF over real HTTP, deterministic concurrency): `patterns.md` next to this file.

## Python equivalent

- pytest with `asyncio_mode = "auto"` if the app is async; `conftest.py` sets harmless defaults for required env vars (`os.environ.setdefault("API_KEY", "test-not-used")`); unit tests never call the network.
- Each test gets its own database: a `tmp_path` SQLite file (monkeypatch every module that reads `DB_PATH`), or, for Postgres-specific SQL, an ephemeral Postgres container in CI at the production major version.
- Drive the real app: FastAPI/Starlette `TestClient` or `httpx.AsyncClient(transport=ASGITransport(app=app))`; Flask `app.test_client()`.
- Autouse fixtures reset module-level singletons and caches between tests.
- Split `tests/unit` (no keys, runs in CI) from `tests/integration` (needs real keys; runs on demand).

## Counter-test discipline (mandatory for fixes)

1. Write the test that encodes the failure.
2. Run it against the UNFIXED code (stash the fix or revert the key line) and confirm it fails or hangs.
3. Re-apply the fix; the whole suite passes.
4. Put the evidence in the close-note: "fails without the fix; all N tests pass with it" (work-log skill).

A test written after the fix may pass with or without it. Step 2 is the only proof it guards anything.

## Known limits (close them elsewhere)

- pg-mem is an emulation. If a query misbehaves only there, verify on a real Postgres before contorting the query.
- An SSRF guard blocks loopback by design, so outbound-fetch behaviour (deadlines, redirects) can't be integration-tested against 127.0.0.1 - unit-test those pieces.
- Tests never build the container image: packaging bugs (a missing COPY) pass green. CI builds the image or the deploy boot-checks it (`docs/agent/ci-cd-and-deploy.md`).

## Browser preview without a database

1. A throwaway harness (untracked, e.g. `scratch/preview.js`) sets the dev-identity and other env vars BEFORE `require("../server")` (they are read at module load).
2. `await data.init(memPool())`, then seed a user and a few realistic items - including the edge cases (empty, long text, many rows).
3. `http.createServer(app).listen(Number(process.env.PORT) || 3999)`.
4. Point the preview tool at it. If that needs a launch-config entry (`.claude/launch.json`), it is git-tracked: revert the temporary entry before committing.

Preview tool gotchas:
- Screenshots can hang on a rendered page: verify with JS evaluation, computed styles and the accessibility snapshot instead, and say the visual judgement is still the human's.
- Clicks can miss small targets while reporting success: dispatch a native bubbling event, `el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }))` (KeyboardEvent for Enter/Esc, `.blur()` for commit-on-blur).
- Re-query nodes from `document` after every mutation; re-renders replace them.

## Stray-server trap

Before sending a request to a locally started server, confirm YOUR instance bound: the listening log line, no `EADDRINUSE`. Prefer a non-default port (`PORT=3999`) and kill stray listeners you started (match on the full command line, never on the interpreter name alone). Treat any reachable database as real data unless you created it in this session. Why: a leftover server from an earlier session can answer on the same port, and if it is connected to a real database, a smoke test changes real rows.

## Output

Report the test file(s), the command, the exit code and the counter-test evidence:
`node --test test/<name>.test.js -> fails without the fix (exit 1); full suite <n>/<n> with it (exit 0)`.

## What NOT to do

- No test against a shared, staging or production database.
- No "verified" without running the suite; no skipped tests to get green.
- No throwaway harness to route around an unrelated broken test - stop and report instead.
- No preview harness or launch-config edit left in the commit.

## Project overrides (fill in)

- Test command: `<npm test | pytest -q>`
- Identity header/cookie used in tests: `<X-Forwarded-Email | session cookie helper>`
- Data-layer init signature: `<data.init(pool)>`
- Preview port: `<3999>`
