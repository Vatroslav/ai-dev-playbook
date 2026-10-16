---
name: note-this
description: Route one fact, result, "we tried X" or "X is done" to the one right place in the repo, using the project's where-to-write-what table, and commit it. Use for "write this down", "note that", "log this", or when someone reports they did, fixed, tried, measured or decided something. Manual /note-this <text>. NOT for adding a dated action (use /todo) or creating a task file (use /tasks).
argument-hint: "[the fact to record]"
---

# Note this (capture router)

Nobody will say where it goes; finding the place is your job. Why: notes written to random files or to personal memory are effectively lost to the team, and asking "where should I put this?" every time makes people stop reporting.

## Routing

Use the "Where to write what" table in the project section of `AGENTS.md` first. If it is missing, use this default:

| Topic | Destination |
|---|---|
| Action with a date or trigger | `/todo` |
| Bug found, not fixing now | issue tracker, or `/todo` with a link |
| Multi-step work, or an idea to park | `/tasks` |
| Decision between alternatives | `docs/decisions.md` (big or hard to reverse: also `docs/adr/` from the template) |
| Measurement, test or usage result | `docs/findings.md` with date, version and sample size |
| Raw user or tester feedback | `docs/feedback.md`, verbatim |
| Gotcha of an external API or service | `docs/integrations/<service>.md` |
| Architecture fact | `docs/architecture.md` |
| Meeting outcome | `docs/meetings/YYYY-MM-DD.md` |
| User-facing change | the release-notes file |
| Correction of the agent's behaviour | `docs/agent/feedback/<name>.md` (template: feedback-memory) |
| "X is done" and a task file or row exists | close it there (`/tasks` done, or flip the row's Status) |
| Only if nothing above fits | memory |

The table isn't locked: if an obvious file exists for the topic, use it and add a row to the project table. If the destination isn't obvious, grep `docs/` for a related file BEFORE creating one; create new files only for new permanent topics.

## Writing rules

- Read the target file first and mirror its format.
- Absolute dates from the system (`date +%Y-%m-%d`); convert "yesterday" and "last Friday".
- Facts verbatim: numbers, names, versions and quotes exactly as given. Add nothing "likely". Label any elaboration of yours as interpretation.
- A record of what was sent or done contains only confirmed facts; a draft is marked as a draft.
- Don't change existing lines unless asked to correct them; permanent docs are rewritten to the current state, the decision log is append-only.
- If one fact belongs in two places (a finding that also closes a task), write both, in one commit.
- Never write secrets, personal data of users, or customer names into the repo.

## Commit

Explicit paths: `git commit -m "docs: <what happened>" -- <paths>`, then the repo's PR flow.

## Output

One sentence: where it went (`docs/findings.md`, "Signup conversion" section). Don't echo the whole entry.
