---
name: next
description: Read-only view of what to work on next - reads docs/todo.md (critical path, its exclusion list, the Active table, due rows) and returns either the one dominant next thing or a full overview. Changes nothing. User-invoked - /next, /next all, /next mine.
disable-model-invocation: true
argument-hint: "[all | mine | AI]"
---

# Next

Reads the tracker and summarizes it; changes nothing. Why: "what should I do next?" answered from memory or from code drifts away from what the team agreed, and offers work that is waiting on something.

## Source

`docs/todo.md` only: `## Critical path to <milestone>` (curated order), its `### Not on this path` list (hard exclusions), the `## Active` table (Status, Owner, Trigger, Due, Depends), `## Recently done`. The archive only on explicit request. Don't open specs, ADRs or code to invent a plan.

Due rows come from the script, never by eye: `python .claude/skills/todo/scripts/todo_tool.py due`.

No `docs/todo.md`: look for `TODO.md`, `ROADMAP.md`, `NEXT.md`. None -> say "No plan written down in this repo", show `git log -3 --oneline` as context only, offer to create `docs/todo.md` from the template, and stop. Never guess a plan from code or commits.

## The exclusion list is the key rule

A row under "Not on this path" is NEVER presented as next, even if its Status is open. "Open" means not done, not workable today. If asked about it directly, show it under "Waiting" with its exact condition.

## Trigger and owner evaluation (against today's date and Recently done)

- Trigger is a code or repo condition -> check whether it happened (merged PR, done row). Met -> actionable.
- Owner `PO` or a trigger that is a product decision -> "Decisions waiting", never actionable for an agent.
- Trigger is an external event (vendor, first customer, a date) -> never actionable now.
- `Depends` on an open row -> not actionable.
- Status `blocked` -> not actionable; show the blocker.

## Steps

1. Get today's date from the system.
2. Arguments: `all` -> full overview. `mine` -> filter to the asking teammate's handle (ask once if unknown). `AI` -> only rows with Owner `AI`.
3. **Fast path (default):** the first open step on the critical path. If it is actionable, print only:
   ```
   Next: <action in words> (APP-NNNN)
   Where we stopped: <one line from Recently done or the linked task file's Status>
   First concrete step: <one line>
   N more open - /next all
   ```
   Not actionable -> one line on what it waits for, then try the next step on the path. If due or overdue rows exist (from the script), add one line: "Also due: <action> (APP-NNNN), <date>". Nothing actionable on the path -> full overview.
4. **Full overview:**
   - **Where we are:** one or two lines from Recently done.
   - **Critical path:** remaining steps, the next one marked.
   - **Due or overdue:** from the script.
   - **Decisions waiting:** rows with Owner `PO` or decision triggers (suggest `/decisions-mode`).
   - **Can do now, off the path:** actionable rows by Prio.
   - **Waiting:** every non-actionable row with its exact condition, including all excluded rows.

## Boundaries

- Read-only: no edits, no commits, no new files.
- Never runs on its own initiative.
- If the tracker doesn't say, it says so. It never invents priorities, plans or dates.
- For freshest state across teammates: `git fetch origin` and read `git show origin/main:docs/todo.md` if the local checkout is behind.
