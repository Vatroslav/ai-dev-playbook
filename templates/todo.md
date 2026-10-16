# TODO

The single tracker for actions AND decisions in this repo. Copy to `docs/todo.md`. Rationale: `docs/agent/planning-and-tracking.md`.

## Rules

- **Add rows through the `/todo` skill**; it computes the ID and checks the table. Hand edits are fine for status flips.
- **One row = one action or one pending decision.** Context lives in a linked file (`docs/tasks/active/<slug>.md`) or under `## Details`; the row holds the action and the link.
- **Status:** `open` | `in-progress` | `blocked` | `done YYYY-MM-DD`. Done is one move: flip the Status cell. The row stays until the sweep moves it to `docs/todo-archive.md` (append-only, never edited).
- **Prio:** `high` (blocks the next milestone) | `medium` (needed before launch) | `low` (nice to have). Prio says how important a row is, not whether it can start.
- **Owner** (who must act for the row to move; independent of Prio): `AI` (an agent can build it now) | `@handle` (needs a teammate's hands or judgment) | `PO` (waits for a product decision) | `design` (waits for a brief or handoff) | `external` (vendor, date, user).
- **Trigger:** the condition the row waits for, written so it can be checked: "PR #12 merged", "signups > 50", "PO picks pricing model". Never "WAIT" or "later". A row with a trigger and no date is checked by the weekly sweep, not by the daily due list.
- **Due:** `YYYY-MM-DD`, or `YYYY-MM` (= last day of that month), or `-`. Use a date only when something real happens on that date; otherwise use a trigger.
- **Postponing:** put the new date in Due and append `(moved from 4 Oct)` to the Action cell. Dates inside cells and notes are written like "4 Oct", never ISO. Rows moved 3+ times go to the sink test.
- **IDs are never recycled.** Prefix `APP-` (pick one per repo), four digits. Next ID: `python .claude/skills/todo/scripts/todo_tool.py next-id` (max over the working tree, the archive and every branch). Never trust a "next is" note.
- **No `|` inside a cell** (it breaks the table). Check the table with `python .claude/skills/todo/scripts/todo_tool.py check`.
- **Details longer than ~5 lines** go to `docs/tasks/active/<slug>.md`, linked from the Action cell.
- **Name rows in words when talking to people**, with the ID next to it ("the CSV export (APP-0007)").

## Active

| ID | Status | Action | Prio | Owner | Trigger | Due | Depends |
|---|---|---|---|---|---|---|---|
| APP-0001 | open | Example: write the threat model (task: `docs/tasks/active/threat-model.md`) | high | AI | - | - | - |
| APP-0002 | open | Example: decide free-tier limits | medium | PO | PO reviews pricing research | - | APP-0001 |
| APP-0003 | blocked | Example: enable payments in production | high | external | provider approves our account | - | - |

## Critical path to <milestone>

The curated order of work for the current milestone. `/next` reads this first.

1. APP-0001 - threat model
2. APP-0002 - free-tier limits

### Not on this path

Rows that are open but must never be offered as "next" (they wait on an external event or belong to a later milestone).

- APP-0003 - waits for the payment provider

## Epics

- **Platform** - reliability, security, tech debt: APP-0001
- **Monetization**: APP-0002, APP-0003

## Recently done

Last ~10 outcomes, newest first. The sweep keeps this short.

- YYYY-MM-DD APP-0000 - one-line outcome

## Details

### APP-0001 - Threat model

Acceptance: covers OWASP Top 10 plus our product-specific risks; reviewed by one teammate.
