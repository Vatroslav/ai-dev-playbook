---
name: sink-test
description: Weekly sparring on tracker rows that have sunk - overdue AND postponed three or more times. Forces an explicit keep / scale down / postpone / close decision instead of another silent re-date. A conversation, not a report. Weekly scheduled task or /sink-test. NOT for general cleanup - use /janitor.
disable-model-invocation: true
---

# Sink test

Three questions per sunk item:
1. If this isn't done in the next two weeks, what happens? (Nothing = not a priority.)
2. If we do this instead of something else, what do we give up?
3. Is it operational (keeps things running) or strategic (changes where the product goes)?

Why: a row moved three times is usually a row nobody intends to do; re-dating it again hides that, and the list loses credibility.

## Steps

1. Today's date from the system.
2. Candidates: `python .claude/skills/todo/scripts/todo_tool.py sunk` (open, overdue, moved 3+ times, no trigger). None -> "Nothing has sunk." and stop.
3. Filter out: external obligations (a vendor deadline, a legal date), rows whose linked task file says blocked. Say how many were filtered and why.
4. Take the top 5 (most moves first, then oldest due date). More than 5 -> "X candidates; top 5 now, the rest next week."
5. Per item:
   a) Context: the full row, due date, postponement history, the `## Status` of the linked task file, its Owner.
   b) Ask the three questions in ONE message, with options:
      - Q1: a) nothing concrete b) someone is waiting c) self-imposed deadline d) opportunity cost
      - Q2: a) nothing important b) a specific other priority c) strategic work d) don't know
      - Q3: a) operational b) strategic c) mixed
      The answer can be as short as "1a 2b 3c".
   c) Recommend (a heuristic; the human decides):

      | Pattern | Recommend |
      |---|---|
      | Q1 nothing + Q2 nothing important | Close |
      | Q1 nothing + Q2 strategic | Close or postpone |
      | Q1 someone waiting or a real deadline | Keep |
      | Q1 self-imposed + Q3 operational | Scale down or postpone |
      | Q1 opportunity cost + Q3 strategic | Keep or scale down |
      | Q3 mixed + Q1 nothing | Scale down - what is the strategic part? |

   d) Action: Keep / Scale down / Postpone (default +2 weeks; offer +1 and +2 months) / Close.
   e) Apply in `docs/todo.md`:
      - Keep -> no change, but ask for one concrete first step and put it in the Action cell or task file.
      - Scale down -> rewrite the Action to the smaller scope, append `(scaled down <D Mon>)`.
      - Postpone -> new Due, append `(moved from <D Mon>)`.
      - Close -> Status `done YYYY-MM-DD`, append `(closed by sink test)`.
      Never move task files yourself; list them for `/tasks` in the summary.
6. Summary: counts per action, plus "task files to archive: ...".
7. Commit `docs/todo.md` with an explicit path and the repo's PR flow.

## Tone

Direct, not moralizing. Five "keep"s in a row is fine. Five postponements in a row -> one line at the end: "5 postponements - next time consider closing some."

## Headless mode

Print the candidates, the context and the three questions per item as lettered options; change nothing. The human answers later ("APP-0012: 1a 2a 3a") and the next interactive run applies it.

## Boundaries

- Touches only the Action, Due and Status cells of the items discussed.
- Never closes or postpones without the human's answer.
