---
name: tasks
description: Lifecycle of task files in docs/tasks/ - start a new task, park an idea in someday, mark a task done, drop it, or move it - always updating the README Contents index of every folder touched and the linked tracker row. Use for "start a task for X", "park this for later", "X is done", "we're dropping X", "move X to active". NOT for a one-line action - use /todo.
argument-hint: "[new | park | done | drop | move] [topic]"
---

# Tasks lifecycle

Keeps multi-step work in task files whose state is always current and whose indexes never lie. Why: the `## Status` section is the only continuity between sessions and teammates, and a skipped index update makes a folder look empty, or complete, when it isn't.

Folders:
- `docs/tasks/active/` - in progress or next up (committed to)
- `docs/tasks/someday/` - parked ideas, not committed, no dates
- `docs/tasks/completed/` - done, solved elsewhere, or consciously dropped

## Iron rule: README indexes

Every folder has a `README.md` with a `## Contents` list (`- [title](file.md) - one line`). Every add, move or delete updates the Contents of EVERY folder touched, in the same commit. If you find an index that doesn't match the folder, fix it in passing and say so.

## Preflight

- `docs/tasks/` missing -> create the three folders, each with a README containing `# <Folder>` and `## Contents`, and say so.
- `git status` shows changes you didn't make -> stop and report.

## New task (or park in someday)

1. Filename: kebab-case, using words the team already uses for the topic. Check `git grep -il "<topic>" docs/tasks` first; if a file exists, update it instead of creating a second one.
2. Starting now or soon -> `active/`; "one day" -> `someday/`.
3. Content from the playbook's `templates/task-file.md`: title, `Created: YYYY-MM-DD`, goal, context, plan with acceptance criteria, and `## Status` for active tasks. Mirror the format of neighbouring files.
4. Add it to the folder's README Contents.
5. Active tasks get one tracker row linking to the file: hand off to `/todo` (Owner and Trigger as appropriate). Someday tasks get no row.

## Done or dropped

1. Fill the close-note: what shipped (the mechanism), where (files, PR, version), how it was verified, what was consciously not done and why. Dropped: why, and what would bring it back.
2. Add a status line at the top: `Status: **completed YYYY-MM-DD** - <solved via X | dropped because Y>`.
3. `git mv docs/tasks/active/<file> docs/tasks/completed/<file>`.
4. Update the Contents of BOTH READMEs.
5. Flip the linked tracker row to `done YYYY-MM-DD` (dropped: `done YYYY-MM-DD` and "dropped" in the action).
6. Dropping a strategic item also gets an entry in `docs/decisions.md` (what was dropped instead of what, and why).

When someone reports something done and a task file exists, archive it right away; don't wait for "please archive".

## Move (someday -> active, or back)

`git mv`, update both READMEs, add `## Status` when activating, and add or remove the tracker row.

## Commit

Commit immediately with explicit paths: `git commit -m "docs(tasks): <new|park|complete|drop> <task>" -- <every path touched>`, then the repo's PR flow.

## Output

One line: `<Task> -> <folder> (README updated, tracker APP-NNNN <added|done>). PR #<n>.`

## Boundaries

- Never deletes a task file; dropped tasks move to `completed/` with the reason.
- Never edits a task's plan or Status beyond what was reported.
