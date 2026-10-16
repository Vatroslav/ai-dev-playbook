# Debugging

Purpose: How to find root causes with an agent without letting it guess, spin or "fix" the wrong thing.
Read when: a bug report, a failing test, "it doesn't work", "nothing changed after deploy", or a performance complaint.

Agents are fast at producing plausible fixes, which is exactly the problem: a fix built on the first hypothesis looks like progress and ships the wrong change. The rules below force evidence first.

## Before touching code

- **Run `git fetch` and compare with origin before diagnosing repo state.** Why: a local copy that is behind origin can show a "bug" that a parallel session has already fixed.
- **Fetch fresh data before diagnosing.** Never diagnose from an old dump, a snapshot or a `last_updated` field.
- **Check the git history of the files you are about to change.** Reverts, hotfixes and heavy churn mark fragile areas.
  ```bash
  for f in src/billing/proration.ts src/billing/invoice.ts; do
    echo "=== $f ==="
    git --no-pager log -8 --oneline -- "$f"
    git --no-pager log -5 --oneline -i --grep='revert\|fix\|regress\|hotfix' -- "$f"
  done
  ```
- **"It doesn't work" usually means "it isn't deployed".** Confirm the running version first: the health endpoint's SHA, the version shown in the UI, `git rev-parse HEAD` on the server. Daemons without auto-reload keep running old code; see "Deployed, but nothing changed" below.

## Root cause on real data and real structure

- **Confirm the root cause on real data before writing a fix.** That means real columns, real rows, real responses and the library code actually installed in `node_modules` or the virtualenv, not what you remember of it. Iterating is fine; assuming structure is not. Why: a fix built on an assumed schema fixes the wrong thing.
- **Trace data lineage down to the right layer:** the lowest one that still has everything you need. For a wrong number on a dashboard, follow it from the chart's query through views to the raw table, and fix it where it first goes wrong.
- **Don't infer what a column or field means from a generic-sounding name.** Check how existing code uses it. Why: a column that looks reusable may already be filtered or transformed for one statistic, and reusing it for another silently gives wrong results.
- **Record each diagnosis with `file:line` references,** marked confirmed (reproduced) or hypothesis, together with the proposed fix and the test that will prove it.
- **If a query only misbehaves on an emulated database (an in-memory Postgres, SQLite standing in for Postgres), check it on the real engine** before bending the query to fit the emulator.
- **If data is off-limits to the agent (personal data, customer records), diagnose from the definitions:** code, SQL, schema. Have a human run queries that return only aggregates or counts. See [Security](security.md).

## Measure, don't correlate

- **One event that lines up in time is not a cause.** For timeouts and slowness, measure per unit (per tenant, per endpoint, per query) before forming an infrastructure hypothesis. Why: an infrastructure explanation (a cold start, a slow network) is easy to believe and often wrong; per-unit numbers show when the cause is one slow query for one tenant.
- **Look at the per-unit distribution or trajectory before quoting an average.** Per user, per day, per level, per request. Why: averages hide bimodality and phase changes ("engaged, then zero input after a certain step"), and the break point is usually the finding.
- **Only compare measurements taken under the same conditions and thresholds.**
- **Check that a measurement measures something.** Push an input to an extreme and confirm the output moves. See [Verification](verification.md).
- **Measure before optimizing, and measure wall time, not step or node counts.** Take a timing breakdown (median, wait vs download, a HAR file, a profiler run) first, and put the numbers in the commit message. Why: a "smarter" algorithm that visits far fewer nodes can still be slower in wall time.
- **Don't add caching (build caches, layer caches, memoization) without measuring before and after.** Why: a cache can make things slower, for example a CI layer cache whose export costs more than it saves.

## Reproduce in the real context

- **Reproduce UI bugs inside their real parent structure,** not in an isolated component. If a fixed-position element "doesn't cover the screen" or "looks transparent", check its ancestors for `transform`, `filter` or `backdrop-filter`, which create a new containing block, and render it through a portal. Why: isolated reproductions give a false green.
- **When someone points at a working reference ("it looks right on the phone"), measure the reference, measure your output, list the concrete differences, and fix them.** Explain afterwards, if at all. Why: explaining a difference doesn't remove it.
- **Work out interdependent layout numbers on paper, then change the CSS once.** If something is a few pixels off, re-derive the arithmetic instead of nudging values. Why: guessing turns into repeated deploy-and-look cycles.
- **Reproduce at the user's real display settings.** Bugs that only appear at a non-integer device pixel ratio (1.5 at 150% OS scaling) don't show up in a DPR-2 mobile preview.
- **Test URL filters and query parameters with two different values and compare.** Why: some sites and APIs silently ignore parameters they don't support, and one value proves nothing.

## A test that fails twice is telling you about the environment

- **If the same test fails a second time, stop rerunning and inspect the environment.** Check for:
  - two dev servers on the same port (both look healthy, requests get split between them);
  - a zombie process holding the port while the new server still prints "Ready";
  - an unseeded or stale local database;
  - a server that swallows exceptions instead of logging them;
  - hot reload restarting the server because you edited source while the test ran;
  - an environment variable set in your shell but not in CI (for example a secret that turns expected statuses into 401).

  Why: rerunning hides the real cause; time goes into the code while the problem sits in the environment.
- **A dev server that prints "Ready" can be lying.** Check who owns the port by PID before trusting it:
  ```bash
  lsof -iTCP:3000 -sTCP:LISTEN                                  # macOS / Linux
  ```
  ```powershell
  Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object OwningProcess   # Windows
  ```
- **Put timeouts on every wait loop:** `curl -s -m 2` inside loops, a maximum number of iterations, and a clear message when it gives up.
- **A failure whose location moves between runs, with clean server logs, points to timing.** Especially right after a deploy: rerun once while tailing the server log before blaming the code, and don't deploy while people are actively testing.
- **If local lint disagrees with CI and CI is clean, CI wins.** Lint only the files you touched.
- **Document local-vs-CI differences in the project instructions** as soon as you find one, so the next session doesn't chase the same false failure.

## Deployed, but nothing changed

- **Suspect caches first:** browser HTTP cache, a service worker, a CDN, a cached download or template file. `curl` the server and grep for a symbol that only exists in the new version, then give the human a visible sign that tells versions apart (the version number or short SHA in the footer or health endpoint).
  ```bash
  curl -s -m 5 https://staging.example.com/ | grep -o 'data-version="[^"]*"'
  ```
- **Check which directory or branch the preview server is actually serving.** Tooling often starts it in the main checkout instead of your worktree, or you are looking at another session's server on the same port. Compare a file's length or a unique string between disk and what the server returns.
- **Restart the dev server after changing values read at config load.** Build-time constants (for example a version injected through the bundler's `define`) are evaluated once; the UI keeps showing the old value until restart.
- **Restart or recreate long-running processes properly.** Daemons without auto-reload keep running old code; `docker compose restart` doesn't re-read `.env` (use `docker compose up -d --force-recreate`); firmware needs a reflash.

## "Nothing happens" when I click

- **Read the browser console first.** Why: errors in event handlers are often swallowed by the UI, and embedded browsers in agent tools suppress `confirm()` and `alert()` and return false, so a confirm-gated action silently does nothing.
- **Then read the network tab:** a request that never fired, a 4xx with a useful body, or a CORS preflight failure.

## Fix discipline

- **Allow at most two fix attempts per failing check.** After that, revert your change (`git checkout HEAD -- <files>`), and report what you tried, what failed and what you suspect. Why: spinning burns time and hands over broken code; a clean revert plus a clear report is more useful.
- **Prove the test catches the bug.**
  1. Write the test that encodes the failure.
  2. Run it against the unfixed code (stash the fix or revert the key line) and watch it fail.
  3. Re-apply the fix and run the whole suite.
  4. Write "fails without the fix; all N tests pass with it" in the PR or work log.

  Why: a test written after the fix may pass with or without it. More in [Testing](testing.md).
- **After fixing a bug in one view or handler, check for the same pattern in siblings that share the logic** (sibling views, copied handlers, the other locale), but don't start an unrequested audit of everything.
- **When a fix depends on a runtime detail, verify it on the live surface.** Example: a cookie set with `Max-Age=0` can be stripped or rewritten by a framework or proxy layer; only the actual `Set-Cookie` header shows what was sent.
- **If the same manual workaround is needed a second or third time, question the tool instead of automating the ritual.** Why: a note saying "expect this, just retry" entrenches a broken dependency that a small config change could often remove.
- **Record closed diagnoses and abandoned approaches** (cause, fix, mitigations the team rejected) in the task or a "Learned" section, so they aren't redone or re-offered.
- **Don't commit hypotheses into permanent docs mid-investigation.** Write the conclusion once it settles.

## Error messages that mislead

| Message or symptom | Often actually means |
|---|---|
| Socket "permission denied" / `EACCES` when binding on Windows | The port is taken or inside a Windows excluded port range (`netsh interface ipv4 show excludedportrange protocol=tcp`) |
| Browser "too many redirects" | A redirect loop, often a session cookie that is never set or never read |
| OAuth "invalid code" or "invalid grant" | Wrong client secret or redirect URI, or the code was already used |
| Container "Started" | Nothing; containers print it and then crash. Check status (`Restarting`), logs and the health endpoint |
| Webhook returns 503 instead of 401 for an unsigned request | The signing secret isn't mounted |
| `curl -f` fails with no detail | `-f` swallowed the body; drop it and print the response |
| `bad interpreter: /bin/bash^M` | CRLF line endings in a shell script; see [Shell and environment](shell-and-environment.md) |
| `git pull`: "Cannot fast-forward to multiple branches" | A concurrent fetch overwrote `.git/FETCH_HEAD`; use `git fetch origin main && git merge --ff-only origin/main` |
| `git worktree remove`: "Filename too long" | Long `node_modules` paths on Windows; the worktree is unregistered anyway, delete the folder separately |
| A command that never returns | It is waiting for input or a pager; see the interactive-commands section in [Shell and environment](shell-and-environment.md) |
| A spreadsheet-backed or federated external table fails | Often transient; rerun once before debugging |
| A reviewer subagent's reply with no verdict line | It probably hit its turn cap; rerun it once and point it at the files it skipped |

**Recognize known harmless noise and move on.** When a CLI prints a warning that you have confirmed is benign, write that down once in the project instructions so nobody chases it again.

## Upstream bug reports

When the bug is in a framework or library, not your code:

- Base the minimal reproduction on the framework's official starter template, with pinned versions.
- Include expected vs actual (with the exact console error), a one-line check command (`curl ... | grep ...`), the root cause with source pointers and a suggested fix, what masks the bug (so others don't "fail to reproduce"), the versions you verified, and links to earlier reports that were auto-closed.
- Keep the repro in its own small repo or `repro/` folder, and rerun it on each new version before removing your workaround.
