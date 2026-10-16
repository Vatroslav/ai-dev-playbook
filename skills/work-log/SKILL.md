---
name: work-log
description: Record engineering work in the task tracker (docs/todo.md) so every item carries its diagnosis and every closed item carries evidence - what shipped, where, how it was verified, what was consciously not done. Use when a fix, feature or review finding is finished or reported done, when a code review produces findings, when the human says "log this", "mark it done", "close that item", and BEFORE starting work that traces to an existing item (it usually holds the diagnosis and the agreed fix). NOT for quick capture of a new idea or for prioritising (use the todo skill and docs/agent/planning-and-tracking.md).
---

# Work log - items with diagnosis, close-notes with evidence

The tracker is not a scratch list. It is the single source of truth for what was found, decided, shipped and how it was verified. Close-notes get re-read months later to answer "why is it like this?" and "did we already try that?".

Why: "fixed" with no mechanism and no evidence gets re-opened, re-diagnosed and re-litigated. A self-contained item lets any session or teammate pick it up cold.

## Preflight

- `docs/todo.md` missing -> `SKIP: no tracker - create it from templates/ first (see docs/agent/planning-and-tracking.md)`.
- Follow the format rules in the header of `docs/todo.md` (table columns, status values, ID scheme, where long details go). This skill defines the CONTENT of items and close-notes, not the layout.
- Dates come from the system clock (`date +%F`), never guessed.

## Opening an item - self-contained

Every item (or its details section/file) states:
1. What is wrong and why it matters - the failure mode for users, not just the symptom.
2. `file:line` references for every claim.
3. The proposed fix, concrete enough to implement, including the test to add.
4. Whether the diagnosis is **confirmed** (reproduced) or a **hypothesis**.

Example details entry:

```markdown
**Public signup crashes the process when the DB is down** (`<file>:<line>`). The only async handler
without the error wrapper; a rejected query becomes an unhandled rejection and the container restarts
in a loop. **Confirmed by reproduction** on the in-memory server: simulated DB outage + one POST -> exit 1.
Fix: wrap the handler. Test: signup with a rejecting pool must return 500 and the next request 200.
```

Review findings: one item per finding, ordered by severity (High / Medium / Low), each with the four points above.

## Closing an item

Flip the status per the tracker's rules and append a close-note answering four questions:
1. **What shipped** - the mechanism, never just "fixed".
2. **Where** - files, PR number, version.
3. **How it was verified** - test name plus counter-test evidence. A close-note without evidence is incomplete.
4. **What was consciously NOT done, and why** - stops the idea from being re-proposed at the next review.

```markdown
_Done YYYY-MM-DD (vX.Y.Z, PR #N): handler wrapped; rejections now reach the JSON error handler ->
500 instead of a crash (<file>). <test file>: hangs without the fix, <n>/<n> tests
pass with it. Not done: response caching for this route - marginal benefit at current traffic._
```

When a human reports doing something themselves (a DNS record, a console setting), close the item with what they reported - their report is the evidence. Say so in the note.

## Committing

`docs(todo): <outcome>` - no version bump. The close may ride in the fix commit (preferred: same branch, before merge) or land right after it. Never leave a shipped fix with its item open. Stage `docs/todo.md` by name and commit with a pathspec - other sessions edit the same file.

## Headless mode

Scheduled or delegated runs may open items (findings) and close items whose evidence is in the run's own output. They never delete items and never change priorities.

## What NOT to do

- No deleting done items to tidy up - the close-note is the value (archive per the tracker's sweep rule).
- No "fixed" without mechanism and evidence.
- No duplicating architecture or deploy docs inside items - link to them.
- No facts about unmerged code recorded as done.
