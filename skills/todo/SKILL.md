---
name: todo
description: Add one row to docs/todo.md with minimal friction - deterministic next ID (working tree, archive and every branch), derived Owner/Prio/Trigger/Due, table check, one write chain (branch, commit, PR). Use for /todo <text>, "add a todo", "note that we need to X", "remind us to X when Y", "put this on the list". Everything added to docs/todo.md goes through this skill. NOT for flipping a row to done (edit the Status cell) or for multi-step work (use /tasks, which adds the row).
argument-hint: "[what to do + optionally when or after what]"
---

# Todo (fast capture)

One description in, one correct row out, with about one approval. Why: hand-added rows get recycled IDs, broken tables and fake dates; a capture that costs ten permission prompts doesn't get used.

Tool: `python .claude/skills/todo/scripts/todo_tool.py` (below: `todo_tool`; Codex: `.agents/skills/todo/scripts/todo_tool.py`). Read the rules at the top of `docs/todo.md` once if you haven't this session.

## Preflight

- `docs/todo.md` missing -> offer to create it from the playbook's `templates/todo.md`; stop until confirmed.
- `git status --porcelain` shows changes you didn't make -> STOP and report; never mix them into this commit.
- Don't run this for things nobody asked to record.

## Input (derive; ask only if truly ambiguous)

- **Action** (required): one clear action in plain words; keep key references (file:line, PR number). Replace any `|` with `/`. Link a context file if one exists.
- **Owner:** `AI` if an agent can build it now with nothing pending; `PO` if it needs a product decision or content; `@handle` if it needs a specific teammate's hands; `design`; `external`. Echo it back.
- **Trigger:** only if the row waits on an event; write it so it can be checked ("PR #41 merged", "signups > 50"). Never "wait" or "later".
- **Due:** a date the user gave always wins. Otherwise only if something real happens on that date. `YYYY-MM` = end of that month. No date is better than a fake date.
- **Prio:** as stated; otherwise `low` for cleanup and research, `medium` for the rest; `high` only if it blocks the current milestone. Echo it back.
- **Depends:** an ID if given, else `-`.
- **Epic:** best fit from `## Epics`; if none fits, say so (don't create epics).
- **Big piece of work** (several steps, needs its own status) -> hand off to `/tasks`, which creates the task file and then this row with a link. Don't duplicate content.
- **Doesn't belong** (busywork that moves nothing, a duplicate of an open row) -> say so and ask before dropping it. Never reject silently.

## Steps

1. `git fetch origin` and start a branch from fresh main: `git switch -c docs/todo-<slug> origin/main`. If main is checked out in another worktree, never take it over and never `reset --hard`.
2. Next ID: `todo_tool next-id` (it scans the working tree, the archive and every branch). Never trust a "next is" note or your own count.
3. Read only what you need: `git grep -n "^## \|^| APP-" docs/todo.md` to find the end of the Active table and the Epics block. Don't read the whole file.
4. Append the row at the end of the `## Active` table (Edit tool): `| APP-NNNN | open | <action> | <prio> | <owner> | <trigger or -> | <due or -> | <depends or -> |`. Add the ID to the chosen epic line.
5. `todo_tool check` must pass (eight cells, unique ID). Fix and re-check if not.
6. Publish in ONE chain (one approval):
   ```
   git add docs/todo.md && git commit -m "docs(todo): APP-NNNN <short action>" -- docs/todo.md && git push -u origin docs/todo-<slug> && gh pr create --base main --title "docs(todo): APP-NNNN <short action>" --body "Adds APP-NNNN." && gh pr merge --auto --squash
   ```
   Drop `gh pr merge --auto` if the repo doesn't auto-merge docs-only PRs. If one link fails, fix that link only; don't rerun the whole chain blindly.

## Output

One line: `Added APP-NNNN "<action>" - owner <owner>, prio <prio> (defaulted), <trigger or due>. PR #<n>, auto-merge armed.`

## Boundaries

- Only `docs/todo.md`. Only adds one row: never flips statuses, edits other rows, sweeps the archive or reorders.
- Never invents a due date to make a row look scheduled.

## Other commands of the tool (used by /next, /janitor, /sink-test)

`todo_tool due` (due today or overdue), `todo_tool sunk` (overdue and moved 3+ times), `todo_tool triggers` (open rows with a trigger), `todo_tool sweep --older-than 14` (archive done rows, fail-closed). Run `todo_tool --help` for details.
