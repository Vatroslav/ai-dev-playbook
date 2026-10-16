# Engineering notes

Purpose: Product engineering practices for agents and teammates building the app - codebase discipline, web backend, third-party integrations, background jobs, LLM features, frontend, user-facing copy, analytics, and a few specialised areas.
Read when: you build or change backend routes, API clients, workers, LLM features, UI, copy or analytics; or you work on an MCP server, scraper, browser extension, Android app or a system of independently deployed components.

Not repeated here (follow the link): tests and harnesses in [testing.md](testing.md); schema, migrations and data fixes in [database.md](database.md); auth, secrets, headers, SSRF, supply chain and error-tracker privacy in [security.md](security.md); CI, containers, deploy and smoke tests in [ci-cd-and-deploy.md](ci-cd-and-deploy.md); "done means you ran it" in [verification.md](verification.md).

Skills that execute these notes (all in `skills/`): `evidence-first` (the coding loop), `backend-route-checklist`, `data-surface-gates`, `api-client`, `verify-without-infra`, `design-fidelity`, `copy-voice`, `spec-format`, `sqlite-migration`, `sql-runbook`, `sql-sync`, `data-sanity-check`; for shipping: `feature-pr`, `release`, `release-note`, `deploy-vps`, `work-log`.

## Codebase discipline

- **Search before you add.** Run at least two searches (by name, by behaviour, by call site) for an existing util, component, endpoint or client, and extend what you find. Why: the default agent move is "just add it", which leaves three functions doing the same job that drift apart.
- **One pattern per concern.** One way to handle errors, shape API responses, validate input, fetch data and name things. When you find two, consolidate them or write down which one wins. Why: agents copy whichever example they read last, so two patterns become five.
- **Every new dependency gets a written reason in the PR.** Prefer the platform and standard library, then a widely used package. Why: each dependency is supply-chain surface, upgrade work and one more thing the next session must learn; simplicity is a feature.
- **Buy, don't build, security primitives:** auth, sessions, password hashing, crypto, OAuth flows. Why: hand-rolled versions fail in ways tests don't show.
- **Deterministic code by default; an LLM API call is an escalation, justified in the commit or PR.** Reviewers ask first: "can this be done without a model?"

  | Never use an LLM for | Use instead |
  |---|---|
  | format validation (email, phone, URL, IBAN, IDs) | zod, validator, pydantic |
  | string manipulation (slug, trim, case, split) | stdlib, slugify |
  | math (percentages, ranges, percentiles, averages) | native code |
  | filtering and sorting by known fields | array methods, SQL |
  | deterministic business rules | if/switch, lookup tables |
  | parsing JSON, CSV, XML, YAML | standard parsers |
  | date arithmetic | date-fns, dayjs, stdlib datetime |
  | enum mapping, type checks, authentication, authorization | plain code |

  Use an LLM only where semantic understanding is required: turning free text into structured data, intent or sentiment where keywords fail, summarising free text, generating variable copy, conversational interfaces, fuzzy matching with no canonical list. A deterministic library (zod, date-fns, fuse.js) always beats a prompt; check the package registry before writing one. Why: cost (zero per call vs. per token), latency (under 1 ms vs. 1-5 s), non-determinism, vendor outages and rate limits, privacy (personal data sent to a vendor needs a data processing agreement and a threat model), flaky tests, and opaque failures ("model returned malformed JSON" instead of a stack trace).
- **Put boundaries between modules and a deterministic contract test on each.** The agent may rewrite a module's internals freely as long as the boundary test passes. Why: agents break things inside modules they don't fully understand; contract tests catch it before push.
- **Strict types.** TypeScript `strict` with no `any`; cast only where a library leaves no choice, with a comment saying why. Python: type hints plus a checker in CI. Why: agents loosen types to make errors disappear.
- **Mark parallel old/new code paths during a migration:** `// MIGRATION-IN-PROGRESS: keep until <cutover condition>, do not delete`. Cutover is one explicit commit that removes the marker and the old path together. Why: agents delete "unused-looking" code and break production before cutover.
- **Know when to switch from "build" to "patch" mode.** Agree a complexity threshold up front (number of entities, endpoints or modules). Signals you crossed it: the agent claims it read a file it only pattern-matched, silently crosses module boundaries, instructions stop having effect, fixes need more iterations. Above the threshold a human (with agent help) writes the plan and spec, and the agent applies bounded diffs ("in file Y, function Z, make this change"). Why: agents are strong from zero to one and weak at fixing across boundaries they don't understand.
- **For N similar units of work, write a playbook after the first one.** Do the first unit slowly by hand, have the agent write `docs/playbooks/<name>.md` (the issue, its cause in our code, files to touch, how to verify, what not to repeat), then run the rest from the playbook as a checklist in a fresh session. Why: without it the agent rediscovers the problem N times and drifts after a few iterations.
- **If the framework version is newer than the model's training data, keep a local text-only copy of that version's docs** and require a grep for the signature before any API call. A class missing from the docs was invented, not undocumented. Why: hallucinated older APIs are guaranteed, not hypothetical.
- **Choose stack components with hard filters first, then trade-offs:** data residency, lock-in and exit cost, operational burden on a small team, how well coding agents know the stack, maturity, predictable cost. Why: an obscure stack means more hallucinated APIs and only manual testing to catch them.
- **Reuse a proven solution from another of your repos before inventing a variant, and never build logic on unverified lists of external values** (production hostnames, CDN domains, third-party IDs). Why: a host list breaks silently when a domain changes; "not localhost" is something you can check.
- **Measure before optimising, and measure wall time, not step counts.** Put the numbers in the commit message. Why: a "smarter" algorithm doing far fewer steps can still be slower in wall time.
- **Generated files say "generated - do not edit" and come from a committed script; manual fixes to generated output live in an override folder the build applies.** Label one-off codegen or mirror scripts "do not run after manual edits". Why: a rebuild otherwise silently drops hand fixes.
- **Data correctness basics.** Money in integer minor units with explicit rounding. Derive dates from the event that defines them (an expiry date), not from calendar arithmetic like "+1 month". Clean legacy encodings once at the boundary (0/1 integers to booleans). Reuse the one canonical filter or definition instead of composing your own. Keep source data names as sent. Why: each of these produces wrong numbers that look plausible.
- **Never claim what you can't prove.** Return types distinguish "proven none" from "gave up" (e.g. `null` vs. `undefined`, or an explicit `status`), and the UI shows "no results / not possible" only on proof, with a way out (retry, undo, broaden the filter). Why: a timeout presented as "impossible" is a lie users act on.

## Web backend

Walk the `backend-route-checklist` skill for every route change and `data-surface-gates` for every surface that shows user data. The rules behind them:

- **Every async handler's rejection reaches the error handler.** Express 4 does not catch rejected promises: wrap handlers (`const ah = fn => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)`), or use a framework that forwards them. The error handler returns a generic message, never internals. Why: a single unwrapped handler can turn a database blip into a process crash loop.
- **Every data function takes the owner id as its first parameter and throws if it is missing.** Handlers never query the pool directly. Why: drivers bind `undefined` as NULL, and the query silently matches nothing or everything.
- **Identity middleware fails closed (401).** A "default dev user" switch is a local-only escape hatch that production never sets.
- **Sharing breaks isolation on purpose, so every new aggregate, count or bulk mutation decides explicitly whether shared rows count.** Why: shared items leaking into "delete all my done items" is the classic bug.
- **Reject API writes without `Content-Type: application/json` (415) and use `SameSite=Lax` cookies.** Why: form posts and bodyless fetches skip the CORS preflight, so a malicious page could fire writes with the victim's cookie.
- **Middleware order is load-bearing:** security headers -> body parser with size cap -> CSRF guard -> public routes -> identity -> per-user limiter -> authenticated routes -> error handler. Public endpoints get per-IP limits plus a global backstop; behind proxies set the trusted-proxy hop count. Why: without the hop count every visitor shares one rate-limit bucket and real users get locked out.
- **Pages that render user data get a strict CSP (`script-src 'self'`, no inline handlers), enforced by a test that greps served HTML and JS for `on*=` attributes.** A new public page also needs: the public-route matcher or proxy skip-list, a 301 from any raw `.html` duplicate to the canonical URL, and logged-out access to its assets. Check that the CSP actually applies to API routes returning HTML or SVG (middleware matchers often exclude `/api/*`).
- **Cap every user-submitted field;** the body-size limit is only the outer net.
- **Mutating routes return the full updated state.** Why: the client re-renders from one source of truth instead of patching local state and drifting.
- **Destructive actions get a confirmation step or soft delete with a recovery window.** Where the user can't confirm in context, send the expected entity id and return 409 if it changed.
- **Throttle every cache-bypassing call per user.** Why: a "refresh" button or poll that skips the cache lets one client set the pace on your most expensive query (denial of wallet).
- **Fetch third-party content server-side** (link previews, images, fonts) so users' browsers don't call third parties, and send every outbound request through the SSRF-guarded client ([security.md](security.md)).

## Third-party API clients

Procedure and examples: `api-client` skill.

- **All HTTP to a provider goes through one request wrapper** that owns auth injection, refresh on 401, 429 with `Retry-After`, backoff on 502/503/504 and network errors, and a timeout. No extra sleep loops on top; no retries on other 4xx.
- **Make the wrapper's failure contract explicit** (returns `null` after retries, or raises) and guard empty bodies.
- **Writes check the success status explicitly.** Why: an unconditional `return true` can hide a write that does nothing for months.
- **Multi-step writes abort before the first user-visible change, and once state has moved they always try to restore it.**
- **A paginated fetch raises if any page fails; it never returns partial data.** Why: partial lists poison diffs and make unfetched items look "deleted" or "never seen".
- **Keep a small exception hierarchy:** credential error = clean stop that waits for a human; re-auth required = clear stored tokens so they are never retried; API error = non-auth failure after retries.
- **Cache calls made on every poll tick,** keyed by entity, written through on user actions. Why: without a cache, every open tab multiplies provider requests by the poll rate.
- **Split bulk or immediately-live writes into plan (read-only, JSON plan plus readable diff) and apply (re-fetch, drift check, write);** use separate read and write tokens where the provider allows.
- **Never hardcode third-party IDs the platform may restrict (they 404), and check which log levels actually reach production.**

## Background workers, scheduled jobs and health

- **A supervisor tells a crash (restart with backoff) from a clean stop (needs a human; don't restart).** Don't add naive container auto-heal that restart-loops on a "re-auth required" state; write that decision down.
- **Never fetch external data inside an HTTP handler.** Serve a snapshot that a background loop refreshes, seeded synchronously at startup. Why: client timeouts are shorter than upstream latency.
- **On error keep the last good value; on a legitimately empty response, clear it.** Why: otherwise the UI either flips to a false state on a network blip or shows stale data forever.
- **The health endpoint reports version, commit SHA, worker liveness (503 when a worker is dead) and error-reporting SDK state** (client bound and DSN parsed, not "env var present"). Health routes that open a DB connection are token-gated. Why: "is my change live?" needs the SHA, and an env var can be present while error reporting is silently off.
- **Scheduled jobs have an exit-code contract:** 0 for "nothing to do" and for partial failures that retry themselves next run, 1 for total failure, which alerts.
- **Alarm on a source only after two consecutive failures, and fail the run after publishing the healthy sources.** Why: one miss is noise, and a run that stays green can hide broken sources for weeks.
- **Monitor each data source's health (consecutive failures, consecutive empty runs, sudden drops) and flag it for a human; never auto-disable a source or rewrite its config from a redirect.**

## LLM features

- **Deterministic first** (table in Codebase discipline). Every new LLM client call carries a written justification.
- **Validate model output like user input:** parse structured output against a schema (zod, pydantic), handle refusals and malformed output explicitly, and never pass it unchecked into SQL, shell, HTML or tool calls.
- **Never put per-request content in prompt blocks marked for caching.** Keep system and persona text constant, sort tool definitions by name, and put retrieved context and user data in the user turn. Why: a cache miss on a large prompt costs several times more on every call.
- **Test that cached blocks are byte-identical across calls and that importing other modules doesn't change them; cache keys leave out volatile inputs** (file mtimes reset on container COPY and git clone, approximate search results wobble, counters drift).

  ```python
  def test_system_blocks_byte_identical_across_calls():
      a = build_system_blocks(); b = build_system_blocks()
      assert [x["text"] for x in a] == [x["text"] for x in b]   # a timestamp or object id kills cache hits

  def test_cache_key_ignores_volatile_inputs():
      base = Bundle(content={"x": 1}, mtime=1.0)
      assert base.key() == base.copy_with(mtime=9999.0).key()      # mtime resets on COPY/clone
      assert base.key() != base.copy_with(content={"x": 2}).key()  # a real change still busts it
  ```
- **Prompts are code with an eval suite.** Scenarios in files (YAML), scored by an LLM-as-judge rubric (1-5, harsh but fair) or exact checks where possible. A prompt change shows before/after scores in the PR, may not drop the score by more than an agreed threshold (e.g. 10%), and new behaviour adds at least two scenarios. CI fails when prompt files change without a change under `evals/`.
- **Use the async SDK client and a timeout for model calls in request paths;** degrade gracefully when the provider is down.
- **Never ask a model to "be random".** Generate randomness in code (seeded, logged) and pass the result in. Why: a model picking "randomly" picks what it likes.
- **Send the vendor the minimum:** strip identifiers you don't need, and record which personal data goes to which provider in the privacy docs.

## Frontend

- **Keep a design-tokens file (e.g. `DESIGN.md` or `tokens.css`) and read it before generating any UI.** Colours exist only there; a grep for colour literals elsewhere must come back empty. Why: agents invent a new grey on every screen.
- **Port design handoffs by transcription, not by memory** (`design-fidelity` skill). Use semantic names in code, never design shorthand ("variant B"), and build one shared component per repeated control.
- **Scale to fit instead of capping with fixed pixels.** Compute the largest size that fits both width and height (or scale everything from one design resolution by a single factor) and write it to CSS variables; never `Math.min(560, ...)`-style caps; fill the available width. Use `100dvh`, `env(safe-area-inset-*)`, `viewport-fit=cover` and `touch-action: manipulation` on mobile. Why: fixed caps break symmetric scaling on large monitors and leave dead space.
- **Work out interdependent layout numbers once, on paper, then change the CSS once.** Keep the table of derived numbers as a comment above the media query; derive values from the padding of the breakpoint where they apply; toggling a side panel must not change the main column's width; verify each breakpoint in each state. If something is a few pixels off, re-derive; never nudge. Why: guessing turns into repeated deploy-and-look cycles.
- **Test at a non-integer device pixel ratio (1.5) as well as on a mobile preset.** Why: rounding bugs at 150% OS scaling don't reproduce at DPR 2.
- **Wrap every `JSON.parse` of `localStorage` in try/catch, and persist progress including undo state.** Why: one corrupted entry must never brick the app.
- **When animating with transforms, measure positions with `offsetLeft`/`offsetTop`, not `getBoundingClientRect()`.** Why: the bounding rect includes the in-flight transform, so measurements jump mid-animation.
- **Keep business logic free of the DOM so it runs in plain Node tests;** keep scratch test files outside `src/`. Why: a `.js` file emitted next to a `.ts` file gets served by the dev server instead of the `.ts`.
- **Add dev-only URL toggles** (`?step=8&seed=42`) that jump straight to the state under test, are stripped from production builds and log when active; expose a dev-only debug handle (`window.app`) so the agent can drive state. When a teammate wants to test, start the dev server and hand them a deep link with the toggles set.
- **The dev server honours the `PORT` environment variable and is registered in the agent's launch config.** Restart it when the version file changes if the version is injected at config load. Why: preview tools assign ports, and a server stuck on the default port shows nothing - or another project's app.
- **Use relative asset paths (`base: './'` in Vite) for anything served from a subpath or iframe.** Why: absolute paths give a white screen on subpath hosting.
- **Test in Firefox (and Safari if you have Apple users) before a public launch, and resume `AudioContext` on the first pointer or key event.** Why: they are the engines that differ materially from Chromium (Edge is Chromium), and a suspended audio context is the usual reason a web app is silent.
- **PWA basics:** push one history entry when entering a sub-screen so the Android back button returns to the menu instead of closing the app; the service worker fetches network-first with `cache: "no-cache"` and uses the cache only offline; its cache name is internal, not the app version. Why: without `no-cache` the HTTP cache can serve an old data file next to a new app file.
- **Guard client re-queries against out-of-order responses** with one monotonic request counter shared by every action that writes the same state.
- **Update only the changed row after a row action;** don't reload an expensive list.
- **Animation-heavy UI:** warm up fonts, sounds and shaders before first use, don't allocate in per-frame code, clamp frame delta (e.g. to 1/30 s) so a tab switch doesn't teleport objects, and stop the loop when idle. Canvas screenshots hang in background tabs, so verify numerically (computed styles, pixel deltas) and leave the visual judgement to a human.
- **Static hosting checks** (script them for CI): every redirect is an explicit 301 with no chains and no source shadowing a real page; internal links and anchors resolve; every asset exists; every page is in the sitemap or `noindex`, never both; structured data parses; cache-bust assets with the commit SHA.
- **No third-party analytics, tracking scripts, fonts or cookie banners unless the privacy policy covers them;** self-host fonts and prefer cookie-less analytics.

## User-facing copy

- **The product speaks, not the people who built it.** Fill in the `copy-voice` skill once with the team's voice; then every string follows it: short, active, one form of address, buttons as verb + object, exact locale-formatted numbers, no AI phrasing, no emojis unless the voice says so.
- **Every string goes into every required locale in the same change, and the second locale is natural, not literal** (ICU plurals, local number and date formats). Why: a screen in one locale is not done, and literal translations read as machine output.
- **Turn mechanical copy rules into catalog tests:** key parity across locales, no empty strings, banned patterns, plural forms through the real translator (see [testing.md](testing.md)).
- **Copy gate:** print all changed copy (all locales) in chat and get an explicit "ok" before the PR merges. Internal admin-tool copy is listed in the PR instead.
- **Never invent a feature, number or promise in copy; don't assume user attributes the app doesn't collect** (gender, age); reproduce user-chosen labels verbatim; use the product's established vocabulary in public text.
- **Keep a glossary of structural terms** (what "session", "run", "workspace" mean) in AGENTS.md and use each term identically in code, event names, docs and chat. Why: an ambiguous word becomes a bug in analytics.

## Telemetry and analytics basics

- **Every event maps to a decision it could change.** The agent proposes the event list with the decision each one informs; the product owner confirms. Why: metrics without a lever only produce dashboards.
- **Set up telemetry before the first public release.** Why: the first days can't be reconstructed later.
- **The client must never hurt the app:** try/catch around everything, fire-and-forget, `keepalive: true`, no personal data, an anonymous per-device id, and an empty endpoint means a deliberate no-op. Derive `env` as dev on localhost or `file://` and prod everywhere else; never keep a list of production hosts.
- **Exclude your own and test traffic:** tag test traffic in one helper (`?test=1`) so it is filtered, not deleted, and read the team's own device or account ids from a maintained list. Reset the baseline before launch. Why: at small numbers, the team's own test sessions are enough to change the conclusion.
- **"Not measured" is null, not zero.** Days before an event existed are null; days with no events are filled with 0. Why: otherwise a new event looks like a drop, and a skipped day makes a dead week look alive.
- **Look at per-unit trajectories (per user, per step, per day) before any aggregate, and count per action, not per session.** Why: an average hides phase changes ("engaged, then nothing after a certain step"), and a session id is a device, not a person.
- **Send "started" only when the activity really began** (not from a constructor or page load), and send "left" on `pagehide`, not `visibilitychange` (a hidden tab is a pause).
- **Keep fixed contract columns found by name** (`ts, session, env, event`), add new columns only at the end, and put event details in a JSON `payload`. Why: a new metric needs no schema change, and inserting a column in the middle shifts old rows.
- **Collector and dashboard are separate deployments;** never redeploy a collector whose URL is baked into shipped clients, and align the collector's and storage's timezones (a mismatch silently shifts daily charts by a day).
- **Measure the experience, not only the outcome.**
- **Dashboards show; the repo explains.** At most a one-line reading hint under a chart; methodology lives in docs.
- **For data you ingest from outside, run an automated sanity check on every load** (`data-sanity-check` skill). It reports; a human decides.

## MCP server development

- **stdout carries JSON-RPC, so every log line goes to stderr.**
- **Validate required env vars at startup and exit 1 with a clear message.**
- **Tool handlers catch errors and return them as results (`isError: true`) instead of throwing.** Why: the model reads the message and can recover; a thrown error is an opaque failure.
- **Coerce numeric parameters (`z.coerce.number()`) and describe every parameter, including formats** ("UTC `YYYY-MM-DD HH:MM:SS`"). Why: models often send numbers as strings.
- **Put organisation-specific mappings (custom field ids) in an external JSON config named by an env var; an unmapped name fails early with the list of valid names.** Why: the upstream error is opaque.
- **Surface 429 `Retry-After` in the error text, cache enum and label lookups lazily, and restart the MCP client after rebuilding the server** (clients keep the old process).

```ts
server.tool("list_notes", "List notes, optionally filtered by project", {
  project_id: z.coerce.number().optional().describe("Filter by project id"),
  since: z.string().optional().describe('UTC "YYYY-MM-DD HH:MM:SS"'),
}, async (args) => {
  try {
    return { content: [{ type: "text" as const, text: JSON.stringify(await api.listNotes(args), null, 2) }] };
  } catch (error) {
    return { content: [{ type: "text" as const, text: formatError(error) }], isError: true };
  }
});
```

## Scraping

- **Pick the source type top-down:** API or JSON endpoint -> RSS/Atom -> JSON feed -> sitemap -> static listing -> homepage -> headless browser -> browser with login. Each step down is several times more fragile. For JS-rendered sites, find the XHR API in the browser's dev tools before reaching for a headless browser.
- **Be a polite, honest client:** a User-Agent with contact info, a global and per-domain concurrency limit, a per-source time budget, one bad source isolated (`gather(..., return_exceptions=True)`), conditional requests (ETag / If-Modified-Since).
- **Retry only 429 (honour `Retry-After`), 502/503/504 and transport errors;** never other 4xx; never disable TLS verification.
- **Parse correctly:** pass raw bytes to parsers that detect encoding, never parse HTML with regex, and sanity-check extracted dates (reject future and implausibly old ones; "today" too often means you parsed the footer).
- **Deduplicate in layers** (canonical URL without tracking parameters -> `rel=canonical` -> content hash), make upserts idempotent, store raw responses so you can re-extract without re-fetching.
- **Test parsers against frozen HTML fixtures, with no live web in CI,** plus one scheduled live smoke test on a stable source.

## Browser extensions

- **Ask for the fewest permissions** (`activeTab` + `scripting` instead of host permissions) and list every permission and network request in the README and store listing.
- **Keep one injected file as the single source of logic** for both the keyboard shortcut and the popup.
- **Find page elements by accessible label first, with a language-independent fallback** (an icon's SVG path), and tag every DOM change with `data-*` attributes so it can be undone exactly.
- **Inject `document_start` CSS to avoid a flash, and derive styles from the site's own stylesheets** rather than a fixed selector list, so redesigns are mostly survived.
- **Build the store zip from an explicit file list, raise the manifest version on every upload, and give each extension its own privacy policy page.**
- **Before reusing a third-party extension, extract and review its code, and remove `update_url` from forked builds** so code changes only when you change it.
- **Automate store screenshots with headless Chromium** (`--load-extension`, `--disable-extensions-except`), rejecting non-essential cookies in the harness.

## Android and WebView apps

- **Extract timing, state and business logic out of framework classes and unit-test it on the JVM;** name tests as sentences about user-visible behaviour, and write in the build file why only that logic is unit-tested. Verify the rest on a device in the real usage context and record the findings.
- **Callbacks the framework fires whenever it likes have no side effects** (reads only), and the app never reports states it doesn't have. Give synchronous feedback before the network response.
- **A single-file web build can ship both inside a WebView and on the web;** guard native bridge calls with `typeof Bridge !== "undefined"`.
- **Version codes, signing and store uploads:** see [versioning.md](versioning.md) and [security.md](security.md).

## Independently deployed components (contracts)

When a server, web client, mobile app or device firmware deploy on different schedules, old consumers meet new producers and the other way round. Order: producer -> contract -> consumer -> docs -> verification.

- **New fields are optional, and consumers default them to a harmless value that never triggers an alarm or an automatic action** ("absent on older servers -> false").
- **Never rename or remove a field while any deployed consumer still reads it.** Add the new one, migrate consumers, remove the old one later.
- **Consumers parse with explicit defaults** and null-check whole blocks; automatic UI switches fire only on a state change, never while the same state persists, and user input turns automation off.
- **Do display-constraint work (truncation, transliteration) on the producer,** not in every consumer.
- **Document the contract in every README that describes it, and verify an OLD consumer (or a fixture of the old response) against the NEW producer** before release.

## Upstream bug reports

When a framework or library bug blocks you, file a reproduction that maintainers can't dismiss:
- start from the framework's official reproduction template, with versions pinned;
- expected vs. actual, quoting the docs, plus the exact console error;
- a one-line check command (`curl -s http://localhost:3000/repro | grep ...`);
- the root cause with source pointers and a suggested fix (note whether the code that runs is compiled output rather than source);
- what masks the bug in "obvious" repros, so nobody "fails to reproduce";
- the affected versions you actually ran, as a table;
- links to earlier reports closed without triage.

## Generated content and simulations

- **Seed generated content by its index,** so item N is always the same; changing the generator changes every item, so treat it as a breaking change and say so.
- **Generated content needs an independent verifier that shares no code with the generator,** checks that labels (difficulty, category) hold, and names the exact item and step on failure.
- **If anything must replay exactly (simulations, multiplayer, bug-report files), decide on determinism on day one:** integer or fixed-point math, named seeded random streams, a fixed timestep, simulation separate from rendering, and a test that fails on floats or unseeded randomness in the simulated state. Why: retrofitting determinism means rewriting every system, and the agent reaches for floats and `Math.random` by default.

## Monetization and product ethics

- **The free tier is never deliberately degraded; a paid tier adds value instead of locking what was free, and users can always export their own data.**
- **The price is visible up front, "dismiss" is as visible as "buy", and upgrades are offered only when the user touches a paid feature.** No nagging, fake urgency, confirmshaming or visual misdirection.
- **"No ads, no tracking, no accounts" can be the product's reason to exist;** then telemetry is added only by explicit decision.
- **Safety-sensitive features never push users toward risk:** no records to beat, no automatic progression, the app never raises limits on its own.
