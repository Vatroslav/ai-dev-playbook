---
name: evidence-first
description: Main coding workflow for any task that writes, modifies, fixes or refactors code - features, bug fixes, refactors, config changes, even one-line edits ("fix X", "add Y", "implement", "refactor", "make it do Z"). Sizes the task, records a baseline, logs every check as a real tool call in a ledger, has a reviewer on a different model attack medium and large changes, and presents an evidence bundle. Task sizing scales effort down for trivial edits, so it is safe to apply broadly. NOT for read-only work (explain, search, summarize) and NOT for shipping a finished change (use feature-pr).
---

# Evidence-first

Credit: the overall shape of this workflow (task sizing, a verification ledger, adversarial review on another model, an evidence bundle) is inspired by Burke Holland's [Anvil](https://github.com/burkeholland/anvil) agent for GitHub Copilot CLI. The text and the ledger script here are written independently for this playbook.

Nothing is handed over until it has been checked, and every check is a real command whose result is on record. Prefer extending what exists over adding something new. Have an opinion: if the request or the requirement behind it looks wrong, say so before building it.

Why this exists: agents report "tests pass" for tests they never ran, write a second helper next to an existing one, and keep patching a failing fix until the diff is unreadable. Each step below closes one of those holes.

If a capability referenced here is unavailable (no reviewer subagent, no IDE diagnostics), do the closest real check and say so in the evidence bundle. Never fake a check.

## Preflight

- No code change requested (question, explanation, search) -> print `SKIP: read-only request` and just answer.
- Not inside a git repository -> print `SKIP: not a git repo - evidence-first needs git for baseline and rollback` and ask how to proceed.
- Python not available (the ledger needs it) -> keep the ledger as a table in your reply and mark the bundle "ledger: manual".

## Challenge the request first

Before any work, check the request on two levels. If either check fails, write a short "Pushback:" note, give the human three choices - go ahead as asked, go ahead your way, or rethink the request - and implement nothing until they pick one.

- How it would be built: it duplicates existing code or adds debt; a simpler route exists; it is too large or too vague to do in one pass.
- What is being asked (the costlier mistake): it breaks behaviour users depend on; it treats a symptom while the code shows a different root cause; its edge cases would surprise or harm users; it rests on a usage assumption that may not hold.

> Pushback: `utils/format.ts` already has `formatRelativeDate()`. A second date helper will drift from it - extending the existing one with a `style` option keeps one source of truth.

> Pushback: the new "delete all" action is permanent and has no confirmation. Recommend a confirmation step, or a soft delete that can be undone for a while.

## Size and risk

| Size | Typical change | What it needs |
|---|---|---|
| Small | a wording fix, renaming a symbol, one setting, a single-line change | implement -> diagnostics + check tiers. No ledger, no review. |
| Medium | fixing a bug, adding a contained feature, restructuring one module | the full loop, one reviewer |
| Large | a feature that spans several files or layers, any change to a red file | the full loop, three reviewers, plan shown and confirmed first |

When in doubt, call it Medium. A single red file makes the task Large.

Risk per file:
- green: new code that changes nothing existing, tests, docs, comments, config
- yellow: existing business rules, signatures other code calls, database queries, UI state
- red: login and permissions, encryption, money, anything that deletes data, schema changes, parallel or async coordination, interfaces other teams or clients call

## Verification ledger

Each check becomes one row in the ledger, and the evidence bundle is printed from those rows rather than written from memory. A check that has no row did not happen. The ledger is a SQLite file in the OS temp directory (one per repo), never inside the repo.

The helper is `scripts/ledger.py` next to this file (stdlib Python, values bound as parameters). Below, `LEDGER` means `python3 <skill-dir>/scripts/ledger.py` (use `python` where `python3` does not exist).

```bash
LEDGER init
LEDGER add <task-id> baseline build --tool npm --cmd "npm run build" --exit 0 --snippet "compiled in 4.2s"
LEDGER add <task-id> after tests --tool pytest --cmd "pytest -q" --exit 1 --snippet "1 failed: test_refund_rounding"
LEDGER add <task-id> review review-logic-reviewer --tool subagent --exit 0 --passed 1 --snippet "VERDICT: PASS"
LEDGER show <task-id>
LEDGER regressions <task-id>
LEDGER gate <task-id> --min-after 2 --min-review 1
```

Task id: a slug, lowercase letters, digits and hyphens (`fix-login-crash`). `--passed` defaults from the exit code; pass it explicitly for verdicts and waivers.

## The loop

Keep the preparation phases (spec through baseline) quiet. Speak up only for pushback, a spec that changed what was asked, or a reuse opportunity.

### Spec
Turn the request into something checkable: find the files it touches (grep/glob), spell out what "done" means, and add the constraints it obviously implies. Show the spec only when it changes what the human asked for.

### Working tree
1. `git status --porcelain`: changes you did not make -> stop and report (another session or teammate may own them). Never fold them into your work.
2. `git rev-parse --abbrev-ref HEAD`: if the harness assigned a branch or worktree, stay on it. On `main` for Medium/Large, create `<type>/<task-id>` from a freshly fetched `origin/main`.

### Understand
What the change must achieve, how you will know it does, what you are assuming, what is still unclear. Ask when a requirement is ambiguous instead of picking one reading. Read any issue or PR the request points to.

### History (Medium/Large)
```bash
for f in <target files>; do
  echo "=== $f ==="
  git --no-pager log -8 --oneline -- "$f"
  git --no-pager log -5 --oneline -i -E --grep='revert|fix|regress|broke|hotfix' -- "$f"
done
```
A file with heavy churn or recent reverts and hotfixes goes into the plan as a warning. Follow pitfalls already recorded in AGENTS.md (project section) and the relevant `docs/agent/` file.

### Survey
Search at least twice: for similar code, for the patterns the repo already uses, for the test setup, and for everything that imports what you will change. Report reuse when you find it:
> Existing code: `billing/proration.ts` already does X. Extending it is roughly 15 lines; a new module would be roughly 200. Extending it.

### Plan
List the files you will change with their risk colour. Large: show the plan and wait for a yes.

### Baseline (Medium/Large) - GATE
No edits before the baseline rows exist: diagnostics for the files you will touch, the build exit code, the test results. If the baseline is already broken, record it as it is and leave it - your job is to not make it worse.

### Implement
Read before you write; copy the patterns next to your change; extend existing abstractions; add tests when the repo has a test setup; keep the diff small. For a bug fix, write the failing test first and record it failing (see verify-without-infra, counter-test discipline).

### Verify

**Diagnostics (always).** IDE diagnostics for the changed files and the files that import them. Without an IDE, use the compiler, type checker or linter, and say which.

**Check tiers - run every tier that applies.**
- Tier 1 (always): diagnostics; the file parses.
- Tier 2 (when the repo has the tooling - look it up, never assume it): build; type check including test files; lint on changed files; tests (the full suite or the relevant part).
- Tier 3 (required when tiers 1 and 2 never executed the changed code): load the module, or write a throwaway script of a few lines that runs the changed path, then delete it. If that is impossible (it needs production credentials, a device, a simulator), record `tier3-infeasible` and why. Skipping it quietly is not an option.

Record every result (Medium/Large). When a check fails, fix it and run it again - two attempts at most. After that, restore the files you changed (`git checkout HEAD -- <files>`), record the failure and write down what it taught you. Minimum `after` rows: 2 (Medium), 3 (Large).

**Adversarial review - GATE (Medium/Large).**
Stage only your own files (`git add -- <files>`, never `-A`) so reviewers read `git --no-pager diff --staged`. Use the reviewer subagents the repo defines in its agents folder (for example `logic-reviewer`, `security-reviewer`, `quality-reviewer`). The reviewer must run on a DIFFERENT model from this session - a model checking its own diff confirms what it meant, not what it wrote.

- Medium (no red files): exactly one reviewer. Default `logic-reviewer`; if the diff touches an external-input surface (routes, webhooks, auth, integrations, outbound fetchers) use `security-reviewer` instead; if the chosen reviewer's model equals this session's model, pick another.
- Large or any red file: all three, spawned in parallel in ONE turn.
- No reviewer subagents exist: spawn a general-purpose subagent on a different model with a hostile-reviewer prompt ("assume it is wrong until proven correct; end with `VERDICT: PASS|FAIL`"). If that is impossible too, record `review-unavailable` and cap confidence at Medium.

Each reply ends with `VERDICT: PASS|FAIL`. Record each as phase `review`, check `review-<agent>`. A reply without a VERDICT line counts as FAIL (usually the turn cap): record it, re-spawn that reviewer once against the SAME staged diff naming the files it skipped, record as `review-<agent>-retry`. Still no verdict -> confidence Low.
For real findings, fix them and run the check tiers and the review again. Two review rounds at most; whatever is still open goes into the bundle as a known issue, with confidence Low.
Agent definitions may be cached by the running session: after editing them, start a new session before trusting the change.

**Production readiness (Large).** Record `readiness-observability` (errors are logged with context, nothing is swallowed), `readiness-degradation` (a failing external dependency is handled), `readiness-secrets` (nothing hardcoded that belongs in env or config).

**Evidence bundle - GATE.**
```bash
LEDGER gate <task-id> --min-after 2 --min-review 1    # Large: --min-after 3 --min-review 3
LEDGER show <task-id>
```
Present nothing until `gate` prints `GATE PASS` (it also fails on a regression: a check that passed in the baseline and fails after).

### Record what you learned (now - the session may end)
Write it where the whole team and every tool will see it - the project section of AGENTS.md (the Commands line, or a short "Learned" list), not personal memory: a build or test command that turned out to work; a pattern in the codebase nobody had written down; something a reviewer caught that your own checks missed, plus the check that would have caught it. Skip the obvious, what is already documented, and anything about unmerged code.

### Present
Only what helps the human decide: pushback, the spec if it changed the request, a reuse opportunity, the plan (Large), a short summary of the change, the evidence bundle, open doubts. Small tasks: the change plus "build passed" with the real exit code.

### Commit
Commit only your files with an explicit pathspec and a conventional type (`git commit -m "fix(scope): ..." -- <files>`), bump the version by intent if the repo uses the bump guard (see `docs/agent/versioning.md`), then ship with the feature-pr skill. Report branch, commit and rollback (`git revert <sha>`).

## Output format (evidence bundle)

```
## Evidence bundle
<task-id> - size S|M|L - risk green|yellow|red
### Baseline        (LEDGER show, phase baseline)
### After           (LEDGER show, phase after)
### Regressions     (LEDGER regressions output, or "None detected.")
### Review          | Reviewer | Model | Verdict | Findings |
Fixed during review: ...
Files: one line per changed file
Checked dependents: modules that import the changed code
Confidence: High | Medium | Low
Undo: git revert <sha>   (or: git checkout <pre-sha> -- <files>)
```

Confidence levels mean exactly this:
- **High**: every tier passed, no regression, every review finding fixed - safe to merge without reading the diff.
- **Medium**: the changed path has no test, or a concern was addressed but not proven, or dependents were not all checked - a human should skim it.
- **Low**: a check still fails, an assumption could not be verified, or a review finding could not be ruled out - say what evidence would raise the level.

## Build/test command discovery

AGENTS.md project section -> ecosystem config (`package.json` scripts, `Makefile`, `pyproject.toml`, `build.gradle*`) -> conventions -> ask the human last. Save a confirmed command where "Record what you learned" says.

## Interactive input rule

Never start a command that prompts (it hangs the tool call), and never hand the human a command that needs their input without saying so. Collect a non-secret value in chat, then pipe it: `printf '%s' "$VALUE" | tool set NAME --data-file -` (`printf`, not `echo`, which adds a newline). Pre-answer confirmations (`--yes`). Secrets are never collected in chat - see `docs/agent/security.md`. Browser OAuth flows need the human's environment: give the exact command and why.

## Headless mode

When no human can answer (scheduled or delegated run): skip the confirmation waits but not the gates. If pushback fails or the task is Large, do not implement - output the pushback and the plan and stop. Otherwise run the full loop, never commit to `main`, and end with the evidence bundle as the run's output.

## What NOT to do

- Never hand over a change that adds a build or test failure (failures that were already there are reported, not hidden).
- Never write "tests pass" without a ledger row (Medium/Large) or a quoted exit code (Small).
- Never go past two fix attempts on one failing check, and never leave a half-fixed change behind.
- Never run the reviewer on the same model as the author when another is available.
- Never "fix" pre-existing lint findings in files you did not touch.
- Never narrate the method; show results.

## Project overrides (fill in)

### Verification commands (use these - don't re-derive)
- Backend changed: `<e.g. make lint && pytest tests/unit -q>`
- Frontend changed: `<e.g. pnpm typecheck && pnpm test && pnpm build>`
- Environment quirks: `<e.g. tests assume TZ=UTC; set it before running them>`
- Tooling missing: record `tooling-unavailable` with the reason; never skip silently.

### Doc-drift gate
Fill in the map in `scripts/doc_drift.py` (or pass `--map docs/agent/doc-map.json`), then for every Medium/Large task:
```bash
python3 <skill-dir>/scripts/doc_drift.py; LEDGER add <task-id> after doc-drift --tool doc_drift --exit $?
```
On FAIL there are only two honest exits: update the doc and re-run, or record a waiver row with `--passed 1 --snippet "waived: <doc> - <reason>"` (pure refactor, typo). A waiver is shown in the bundle, never a silent pass.

### PR requirement checks
- `no-stubs` (FAIL on any hit): `git --no-pager diff --staged | grep -E '^\+' | grep -nE 'TODO|FIXME|NotImplementedError|not implemented'`
- `tests-present` (WARN, caps confidence at Medium): non-trivial logic changed under `src/` with nothing changed under `tests/`. Don't flag pure refactors or doc/config diffs.
- `evals-present` (FAIL): prompt files or agent definitions changed without a change under `evals/` (see `docs/agent/engineering-notes.md`, LLM features).

### Project invariants for reviewers
- `<e.g. every data function takes the owner id first>`
- `<e.g. tool definitions sorted by name; no per-request text in cached prompt blocks>`
