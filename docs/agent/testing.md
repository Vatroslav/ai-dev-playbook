# Testing

Purpose: how to write tests that catch real failures, prove they can fail, and stay honest as the code changes.
Read when: before writing or changing tests, before calling a fix "done", and when adding a guard, CI script or lint rule.

General verification rules (run it, report what you did and didn't check) are in [verification](verification.md). Database-specific testing is in [database](database.md); CI wiring in [CI/CD and deploy](ci-cd-and-deploy.md).

## Principles

- **Tests change in the same commit as the code they cover.** Why: a test updated "later" never is, and the next session can't tell which one is wrong.
- **Never merge with failing or skipped tests, and never get to green by deleting, skipping or weakening a test.** A skipped test is debt you fix now. Why: a skip turns a known failure into an invisible one.
- **If an existing test is broken for reasons unrelated to your change, stop and report.** Don't build a throwaway harness to route around it. Why: the workaround hides the breakage from everyone else.
- **Before shipping, answer "what can go wrong here, and how would I know?"** If the answer is "I don't know", the gate has not passed: you need a test, a monitor or a rollback plan.
- **A problem humans have caught twice becomes an automated check** (test, lint rule, CI script, hook). Why: good intentions fail again on the same issue; a check doesn't get tired.
- **Green CI is not deploy safety if CI never builds the deploy artifact.** Unit tests don't build the container image; build it in CI or boot-check it at deploy (see [CI/CD and deploy](ci-cd-and-deploy.md#containers)).

## Prove that the test can fail

A test that cannot fail is worse than no test, because it produces confidence.

- **Counter-test discipline for every bug fix:**
  1. Write the test that encodes the failure.
  2. Run it against the unfixed code (stash the fix or revert the key line) and watch it fail or hang.
  3. Re-apply the fix; the whole suite passes.
  4. Write the evidence in the PR or task close-note: "fails without the fix; all N tests pass with it".
  Why: a test written after the fix may pass with or without it.
- **Test your guards by making them fire.** Run ESLint programmatically on fake code that MUST fail and assert it fails on your rule specifically. Run CI scripts as a subprocess, the way CI runs them, on the CI operating system. Pipe-test agent hooks with a sample payload. Why: a broken lint selector still loads and `pnpm lint` still passes, and a CI script that works on your machine can silently check nothing on the CI operating system while the step stays green. The [CI script tests](../../ci/scripts/check-version-bump.test.mjs) show the pattern.
- **Build destructive test strings from parts.** A hook test whose command text literally contains a destructive command triggers real permission prompts; the human sees only the prompt, not your intent, and correctly denies it.
- **Anchor every "nothing matches" assertion against silently-green outcomes.** Assert there is something to check (`expect(files.length).toBeGreaterThan(0)`), and assert that a known historical case is matched. Strip comments before asserting that a pattern is absent. Why: a broken regex or an empty glob passes "no violations found" on an empty set.
- **Every guard test has a positive control:** legitimate traffic still passes. Why: it catches the over-broad fix that blocks everything, which a negative test alone rewards.
- **Keep known exceptions as exact counts, not upper bounds** (`expect(cspBlocks).toHaveLength(1)`, not `<= 1`). More fails (a new bug); fewer also fails (upstream fixed it, so delete the exception). Why: exceptions must not outlive their reason.
- **Every configurable threshold gets two rows: one that passes it and one that fails it** (exactly at the limit, and one below). Why: off-by-one at the boundary is the most common bug, and a test with only typical values never sees it.
- **Check that a measurement measures something.** Push an input to an extreme and confirm the output moves. Identical results across variants are suspicious. A live check must use an input where the change is visible. Why: a "verified live" check passes trivially when the sample is already in the target format.

## What to test first

In order of what hurts most when it breaks silently:

1. Authentication, session and permission gates; tenant and user isolation (use a second account or a second tenant).
2. Data-access boundaries: parameters bound, only approved tables or views reached, ambiguous identity fails closed.
3. Privacy and display thresholds, including numbers that can be derived by subtracting two published aggregates.
4. Money, dates and other calculations with rounding.
5. The version guard and other CI scripts.
6. Message catalogs: key parity across locales, no empty strings, plurals through the real translator.
7. Configuration that fails silently (a setting the driver ignores, a secret that isn't mounted).

| Layer | File suffix | Runs | Notes |
|---|---|---|---|
| Unit: pure logic | `*.test.ts` next to the module | every PR | no network, no keys, no DB |
| Route / server action with mocks | `*.test.ts` | every PR | assert refusal and order, not just the happy path |
| Boundary contract | `*.test.ts` | every PR | a mocked client records what is sent |
| File-level contract | `*.test.ts` | every PR | schema, migrations, workflow YAML, config read as text |
| DB | `*.db.test.ts` | every PR, ephemeral Postgres | real app role, own Vitest config, no file parallelism |
| Live integration | `*.integration.test.ts` | locally or scheduled | needs real credentials; skips only when fully unconfigured |
| E2E smoke | `*.spec.ts` (Playwright) | manually before prod, or nightly | small, against staging |
| Post-deploy smoke | in the deploy workflow | every deploy | health, SHA, error tracker, webhooks; see [CI/CD and deploy](ci-cd-and-deploy.md#post-deploy-smoke-test) |

## Test the real path

- **Drive the real app over HTTP on an ephemeral port** (`listen(0, "127.0.0.1")`), with the same identity header the production auth proxy sets. Different identities are different users, which is how isolation gets tested. The app module must export the app and only call `listen()` when run directly. See the skeleton below.
- **Seed data through the public API, not by writing to the database.** Why: the API is the contract under test, and DB-level seeding skips the validation real users go through.
- **Run the production SQL against an in-memory Postgres (`pg-mem`)** when you have no database in the test environment: the same queries, `$1` parameters and transactions, through an injectable pool. Its limit: it is an emulation. If a query misbehaves only there, verify it on real Postgres before bending the query to fit.
- **Test row-level security, grants and constraints on a real Postgres** at the production major version, connected as the real app role (no superuser, no `BYPASSRLS`); use the owner connection only for seed and cleanup. Each DB test file uses a unique ID prefix and cleans up before and after. See [database](database.md#multi-tenant-isolation).
- **Server action and route tests assert refusal and order:** an unauthorized caller never reaches the data call (`expect(findMember).not.toHaveBeenCalled()`); an infrastructure error propagates instead of turning into "forbidden"; lookups are scoped to the session's tenant; privileged values sent in the request are ignored; the audit entry is written. With Vitest: `vi.hoisted` + `vi.mock`, then `await import()` the module under test; reset mocks in `beforeEach`; restore `process.env` in `afterEach`.
- **Boundary contract tests record what is sent:** the mocked client captures the query, and the test asserts that user input is in the parameters and never in the SQL text, that only the approved function or view is called, and that two rows for one identity throw instead of picking one.
- **Integration tests against live services skip only when their fixture is completely absent, and fail loudly when it is half configured:**
  ```ts
  const email = process.env.TEST_FIXTURE_EMAIL, uid = process.env.TEST_FIXTURE_UID;
  if (Boolean(email) !== Boolean(uid)) throw new Error("Incomplete fixture: set BOTH or NEITHER.");
  describe.skipIf(!(email && uid))("live boundary integration", () => { /* ... */ });
  ```
  Why: a silent skip gives a false green on the only real boundary test.
- **Unit tests need no API keys;** tests that need real keys live in a separate folder or suffix and are not part of the PR gate.
- **In CI, a test that depends on a tool fails when the tool is missing; it doesn't skip.** Locally a skip is fine.
- **Watch for environment variables in a developer shell that change behaviour** (an auth secret that turns expected statuses into 401). Run with them unset to match CI.
- **When the risk is connection behaviour (websockets, retries, timeouts), test against a real running server rather than mocks.** Put slow, timer-dependent tests behind a flag (`--slow`). Tag test traffic in one helper (`?test=1`) so analytics filters it instead of someone deleting rows later.
- **Preview against realistic data, not idealized mocks.** Pick the real scenario with the most edge cases (sparse data, many transitions, narrow windows). Why: idealized mocks hide overlap and empty-state bugs, and raise false alarms.

## File-level contract tests

Cheap tests over files that catch whole classes of drift that make no noise:

- **Schema and migrations:** every tenant table has RLS enabled and forced, plus a policy; no role is ever granted `BYPASSRLS`.
- **Workflow YAML:** the deploy workflow requests OIDC and never uses a key; the CI workflow has no `id-token: write`; every action is pinned to a 40-character SHA; no workflow mentions production resources.
- **Config:** a setting lands where the library actually reads it. A connection-limit URL parameter can look like a pool limit while the driver adapter ignores it; the test asserts the value is passed to the adapter and that the dead form never returns.
- **Doc/code consistency:** a doc claim and a code marker are checked together, so changing one without the other fails.
- **Registry and content:** files on disk equal the registry exactly; IDs the UI depends on are pinned; the loader rejects path traversal.
- **Health probes that mirror real queries change in the same commit as the query signature.** Why: a probe on the old signature raises a false "degraded" alert, and false alarms train people to ignore real ones.

## Determinism

- **Pin the clock to force races and edge cases** (`Date.now = () => 1_700_000_000_000` inside `try/finally`; `vi.useFakeTimers()` in Vitest). Why: "same millisecond" collisions never happen on a fast laptop, only in production.
- **Inject failures after boot:** wrap the DB pool so queries can be made to reject, and assert the process returns 500 and keeps serving. Why: one unwrapped async handler can turn a database blip into a crash loop.
- **All randomness comes from named, seeded streams; no `Math.random` in state.** Seed procedural content by its index, so item N is always the same, and treat a generator change as a breaking change. For real-time simulations, decide on determinism on day one, so tests replay seed plus inputs to a checksum and a bug report becomes a reproducible file. Why: retrofitting determinism means rewriting every system.
- **Before tuning weights for variety, simulate thousands of seeds** and look at the distribution, not at three samples.
- **Generated content needs an independent verifier that shares no code with the generator** (its own rule checks, its own solution counter). It names the exact item and step that failed. Why: a verifier built on the generator's code inherits the generator's bugs.
- **Anything used as a cache key must be byte-identical across calls.** For LLM features: system prompt blocks are identical across calls, and importing other modules doesn't change them; per-request content never goes into a cached block. Cache keys leave out volatile inputs (file mtimes reset on clone and `COPY`; health counters drift). Why: one leaked timestamp turns every request into a cache miss at several times the cost.

## Domain notes

- **Migrations:** test on a fresh database and on a copy of a pre-change database. See [database](database.md#migrations).
- **Parsers and scrapers:** test against frozen fixture files (saved HTML, JSON, CSV); no live web in CI. One scheduled live smoke test catches upstream changes.
- **LLM features:** a separate eval suite (scenario files plus an LLM-as-judge rubric with numeric scores). A prompt change needs before and after results in the PR, a regression threshold (for example no more than a 10% score drop), and new scenarios for new behaviour. Unit tests mock the model.
- **Calculations and money:** integer minor units (cents) with explicit rounding; reference cases from published worked examples, each with its source cited above the test; cases computed only from the formula are labelled "(derived)"; inverse functions return the smallest matching input.
- **Message catalogs:** identical key sets in every locale, no empty strings, plurals tested through the real translator, not a re-implementation.
- **Android:** pull timing, windowing and state logic out of framework classes into plain Kotlin and unit-test it on the JVM (`./gradlew testDebugUnitTest`). Name tests as backticked sentences about user-visible behaviour, cover exact boundaries, and say in the build file why only that logic is unit-tested. Gotcha: comparing a nullable `Long?` with `assertEquals` needs Long literals (`2_000L`). Verify the rest on a device.
- **Games and canvas apps:** keep rules free of the DOM so they run in plain Node; expose a dev-only debug handle and step `update(1/60)` by hand for deterministic browser checks.

## Conventions

- **Suffixes:** `*.test.ts` for Vitest, `*.db.test.ts` for database tests, `*.integration.test.ts` for live services, `*.spec.ts` for Playwright only, `*.test.mjs` for `node --test`.
- **Every test file starts with a comment saying why it exists:** which attack, incident or finding it guards against, and why the failure would otherwise be silent. Test names are behaviour sentences. Why: the suite then reads as documentation, and nobody deletes a test whose reason they can see.
- **Typecheck the whole project, test files included, in CI** (`tsc --noEmit`). Why: Vitest and esbuild strip types, and framework builds skip test files, so a type error in a test reaches main unnoticed.
- **Exclude agent worktrees and generated code from discovery:**
  ```ts
  // vitest.config.ts
  import { defineConfig, configDefaults } from "vitest/config";
  export default defineConfig({
    test: {
      include: ["**/*.test.ts", "**/*.test.tsx"],
      exclude: [...configDefaults.exclude, ".claude/**", ".next/**", "generated/**", "e2e/**",
        "**/*.db.test.ts", "**/*.spec.ts", "scripts/*.test.mjs"],
    },
  });
  ```
  DB tests get their own config (`include: ["**/*.db.test.ts"]`, `fileParallelism: false`, a setup file that loads env before the DB module is imported).
- **Keep scratch test files outside `src/`.** Why: a stray `.js` emitted next to a `.ts` file can be served by the dev server instead of the source.
- **No retries in E2E (`retries: 0`).** A flaky test is a finding, not noise.

## Manual verification before "done"

Automated tests are no substitute for using the feature. Before reporting done (details in [verification](verification.md)):

- **Use it like a user:** the happy path, then empty, wrong, maximum-length input, refresh mid-flow, the back button. Press every button. Reach the success state and the failure or stuck state. Reload: persisted progress must come back.
- **Console clean, no 404s in the network tab.**
- **Log in with a second account** (another role or tenant) and try to see or change the first account's data. Why: it is the cheapest way to catch an access-control bug.
- **Mobile viewport, then reload.** Test in Firefox and Safari before a public web launch; they run engines other than Chromium (Edge and most other desktop browsers are Chromium).
- **Dev-only URL toggles** jump straight to the state under test (`?step=8`, `?seed=42`, `?plan=pro`). They are inert in production builds and log to the console when active.
- **Auth-gated UI the agent can't log into:** use a temporary unauthenticated probe page with fake data, and delete it before committing.
- **Embedded agent browsers are unreliable for visual checks** (screenshots hang, coordinate clicks miss). Verify with DOM queries, computed styles and the accessibility tree, and say plainly that pixels were not seen.
- **E2E smoke against staging:** assert HTTP status, a key `data-testid` and zero console errors per page; never assert on copy, screenshots or concrete numbers. Keep it small (around ten specs); when it starts flaking, cut it rather than patch it. A saved login session file is a password: keep it under a path the agent cannot read.

## Skeletons

**1. Vitest: a threshold test with both sides of the boundary, plus an anchored file contract.**

```ts
// src/reports/min-group.test.ts
/**
 * Guards: a group smaller than the configured minimum is never shown.
 * Silent otherwise: one person's numbers become visible as a "group" of one.
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { suppressSmallGroups } from "./min-group";

const MIN = 10;

describe("suppressSmallGroups", () => {
  it("keeps a group exactly at the minimum", () => {
    expect(suppressSmallGroups([{ key: "a", n: MIN }], MIN)).toHaveLength(1);
  });
  it("drops a group one below the minimum", () => {
    expect(suppressSmallGroups([{ key: "a", n: MIN - 1 }], MIN)).toHaveLength(0);
  });
});

describe("deploy workflow invariants", () => {
  const yaml = readFileSync(".github/workflows/deploy-staging.yml", "utf8");
  const uses = [...yaml.matchAll(/uses:\s*(\S+)/g)].map((m) => m[1]);

  it("has something to check (anchor against a silently green regex)", () => {
    expect(uses.length).toBeGreaterThan(0);
  });
  it("pins every action to a full commit SHA", () => {
    for (const u of uses) expect(u, u).toMatch(/@[0-9a-f]{40}$/);
  });
});
```

**2. node:test: the real app over HTTP on a free port, on an in-memory Postgres.**

```js
// test/isolation.test.js
/**
 * Guards: no user can read or change another user's rows (the top multi-tenant risk).
 * Runs the real routes and the real SQL; seeds through the API.
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { newDb } = require("pg-mem");
const app = require("../server");   // must not listen or connect on require
const data = require("../data");    // data.init(pool) accepts a pool override

let server, base;
test.before(async () => {
  const { Pool } = newDb().adapters.createPg();
  await data.init(new Pool());
  server = http.createServer(app);
  await new Promise((r) => server.listen(0, "127.0.0.1", r));  // port 0 = any free port
  base = `http://127.0.0.1:${server.address().port}`;
});
test.after(async () => {
  await new Promise((r) => server.close(r));
  await data.close();
});

const call = (method, path, user, body) =>
  fetch(base + path, {
    method,
    headers: { "content-type": "application/json", "x-forwarded-email": user }, // what the auth proxy sets
    body: body && JSON.stringify(body),
  });

test("a user cannot read another user's item", async () => {
  const created = await (await call("POST", "/api/items", "a@example.com", { text: "private" })).json();
  const res = await call("GET", `/api/items/${created.id}`, "b@example.com");
  assert.equal(res.status, 404);
});

test("positive control: the owner still can", async () => {
  const created = await (await call("POST", "/api/items", "a@example.com", { text: "mine" })).json();
  assert.equal((await call("GET", `/api/items/${created.id}`, "a@example.com")).status, 200);
});
```

**3. Vitest: prove a lint rule fires (negative test plus positive control).**

```ts
// eslint.config.test.ts
/**
 * Guards: every exported server action calls an auth guard. A broken selector still loads and
 * `pnpm lint` still passes, so the only proof is code that MUST fail.
 */
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const eslint = new ESLint();
const messages = async (code: string) =>
  (await eslint.lintText(code, { filePath: "app/x/actions.ts" }))[0].messages.map((m) => m.message);

describe("server action guard rule", () => {
  it("flags an unguarded export in a 'use server' file", async () => {
    const m = await messages(`"use server";\nexport async function save() { return 1; }\n`);
    expect(m.filter((x) => x.includes("Server action without a guard"))).toHaveLength(1);
  });
  it("passes when a guard is called", async () => {
    const m = await messages(
      `"use server";\nimport { requireUser } from "@/lib/session";\nexport async function save() { await requireUser(); }\n`,
    );
    expect(m.filter((x) => x.includes("Server action without a guard"))).toHaveLength(0);
  });
});
```
