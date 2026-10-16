---
name: janitor
description: Weekly hygiene of docs/todo.md and docs/tasks/. Phase A acts by itself - sweeps done rows older than 14 days into the archive (script with fail-closed checks) and dates trigger rows whose condition has provably been met. Phase B only proposes - stale rows, tracker/task-file mismatches, broken table rows. Weekly scheduled task or /janitor. NOT for items that keep getting postponed - use /sink-test.
disable-model-invocation: true
---

# Janitor

Keeps the tracker small, true and complete without anyone remembering to. Why: done rows bloat the file every session reads; trigger rows have no date, so the daily due list never shows them and they stay invisible for months unless something checks their condition.

Tool: `python .claude/skills/todo/scripts/todo_tool.py` (below: `todo_tool`). Never compute dates, IDs or counts by eye.

## Preflight

- `docs/todo.md` missing -> `SKIP: docs/todo.md missing`, stop.
- `todo_tool check` fails -> report the problems as Phase B item "Broken rows", skip Phase A (never sweep a table that doesn't parse), continue with Phase B.
- Get today's date from the system (`date +%Y-%m-%d`). Never guess it.
- Work on a fresh branch from `origin/main` (headless: in a fresh worktree, `git -C <worktree>` for every command). If `git status` shows changes you didn't make, stop and report.
- OK -> `Preflight OK: <N> active rows, last change <git log -1 --format=%cs -- docs/todo.md>`.

## Phase A (acts)

### A1. Sweep done rows

1. `todo_tool sweep --older-than 14 --dry-run` and read the list.
2. `todo_tool sweep --older-than 14`. Exit code 2 = an integrity check failed and nothing was written: report it and skip to Phase B.
3. Refresh `## Recently done`: for each swept row add `- YYYY-MM-DD APP-NNNN - <one-line outcome>` (newest first; the outcome is your summary of what shipped, from the row and its details). Keep the last 10 lines; older lines are deleted (the archive holds them). Remove swept IDs from the `## Epics` lines.
4. Run `todo_tool check` again; it must pass.

### A2. Trigger sweep

`todo_tool triggers` lists open rows with a trigger. Classify each:
- **MET** -> date it (below).
- **NOT MET** -> count only.
- **CAN'T TELL** -> a direct question in the output; don't touch the row.

Cheap checks only:

| Condition | Allowed check |
|---|---|
| Internal work ships ("PR #41 merged", "auth done") | tracker status, task file Status, `git log origin/main`, `gh pr view` |
| Someone replies | read-only look at the issue or PR thread |
| A number crosses a threshold | the metrics file vs the threshold |
| Public event (a release, a policy change) | at most ONE web search per run, spent on the row waiting longest |
| Our own future work | MET only if it is scheduled in the tracker |
| A product decision | CAN'T TELL (it belongs in `/decisions-mode`) |
| Only a human knows | CAN'T TELL |

Anything costlier -> CAN'T TELL.

Writing a MET row: set Due to the next working day (Mon-Thu +1 day, Fri +3, Sat +2, Sun +1); it is a review date, not a deadline. Replace the Trigger cell with `trigger MET <D Mon>: <original condition> - <evidence>`. An existing later due date is replaced; an earlier one is kept. Never judge priority.

### A3. Commit

Commit only the tracker files, with explicit paths: `git commit -m "docs(todo): janitor - swept N, dated M trigger rows" -- docs/todo.md docs/todo-archive.md`, push, and open a PR (arm auto-merge if the repo uses it for docs-only changes). Nothing changed -> say so, no commit.

## Phase B (proposes only, in chat)

- **B1. Stale rows:** open rows with no Due and no Trigger whose line hasn't changed in 90+ days (`git blame --date=short docs/todo.md`, once). Propose: give it a trigger, a date, or close it.
- **B2. Mismatches:** a task file in `docs/tasks/active/` whose tracker row is done or swept (propose `/tasks` archive), or an open row linking to a task file in `completed/`. README `## Contents` lists that don't match the folder.
- **B3. Broken rows:** whatever `todo_tool check` reported.
- **B4. Not on the critical path but marked high priority for 30+ days:** propose moving it onto the path or lowering it.

## Output

```
# Janitor - YYYY-MM-DD
Swept: N rows (APP-..., APP-...) -> docs/todo-archive.md
Triggers: M met (dated), K waiting, P can't tell
### Met
- APP-NNNN <action> - "<condition>" met: <evidence>. Due YYYY-MM-DD
### Can't tell
- APP-NNNN <action> - question: <what would settle it?>
### Proposals
- B1 stale: APP-NNNN <action> - untouched since <date>: trigger, date or close?
- B2 mismatch: ...
- B3 broken: ...
PR: #<n> (or "no changes")
```

## Headless mode

Run Phase A and print Phase B as above; ask nothing. CAN'T TELL rows and all proposals stay in the output for a human. If any step fails, report it and continue with the next phase; never retry a failed sweep with relaxed checks.

## Boundaries

- Phase A touches only done rows older than 14 days (via the script) and the Due and Trigger cells of MET rows.
- Never deletes, reprioritizes, reassigns or closes an open row. Never moves task files.
- Never writes a separate report file.
