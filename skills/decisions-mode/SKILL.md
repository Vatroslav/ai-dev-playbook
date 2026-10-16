---
name: decisions-mode
description: Low-energy decision mode - serves pending product decisions from docs/todo.md one per message, in three lines with a mandatory proposal, answerable yes / no / skip / stop, and records each answer immediately. User-invoked - /decisions-mode, "let's clear my decisions", "I have 10 minutes, what do you need from me?".
disable-model-invocation: true
---

# Decisions mode

Most stalled rows wait on one human decision. The cost isn't deciding, it's reconstructing the context. The agent does the reconstruction; the human gets one sentence and a proposal. Why: a list of ten open questions with background gets postponed; one question at a time gets answered.

## Preflight

- `docs/todo.md` missing -> `SKIP: no tracker`.
- No rows with Owner `PO` (or a trigger that is a product decision) -> "No decisions waiting." and stop.

## Step 0: shrink the queue

For each candidate, ask: does it need the product owner's judgment, or was it parked out of caution?
- **Decide yourself** (and record it as yours): naming, display formats, work order, technical choices within the agreed stack.
- **Leave to the human:** product direction, scope, pricing, user-facing copy and brand, user privacy, money, anything hard to undo.
- In doubt -> leave it to the human.

## Step 1: order

By Prio (high first); within the same Prio, the easier decision first. Anything due today or overdue goes first, with one word of why.

## Step 2: serve ONE decision, exactly this shape

> **<what it's about, one sentence, plain words>**
> I suggest: <what I'd do, one sentence>
> OK?

No IDs, file names or jargon; no justification unless asked; no "or" in the question - pure yes/no. A proposal is mandatory; never a bare "what do you want?". Read the linked task file and the decision log first so the proposal doesn't contradict an earlier decision.

## Step 3: handle the answer

- **yes** -> record it.
- **no** -> the proposal falls; don't argue. If they said what they want instead, record that; otherwise leave the row open.
- **skip** -> drop it for this session, no comment.
- **stop** -> stop immediately, then do Step 5.
- A question back -> answer in at most three lines, then re-ask the same decision.

## Step 4: record immediately (before serving the next one)

- Tracker row: append `(PO <D Mon>: <decision>)` to the Action cell; update Owner (unblocked -> `AI` or the teammate who builds it), Status and Trigger; a decision that closes the row -> `done YYYY-MM-DD`.
- `docs/decisions.md`: one entry (X instead of Y, reason, confirmed by, "decisions mode").
- Decisions you made yourself in Step 0: record them the same way, marked as yours, so the human can overturn them.

## Step 5: end

Commit once with explicit paths (`docs/todo.md`, `docs/decisions.md`) and the repo's PR flow. Then at most five lines: what was decided, what you decided yourself, what an agent can now build without waiting.

## Boundaries

- One decision per message. Never batch.
- Never reopens a decision already in the log unless the human brings new information.
- Never writes anything the human didn't confirm, except the Step 0 decisions, which are labelled as yours.
