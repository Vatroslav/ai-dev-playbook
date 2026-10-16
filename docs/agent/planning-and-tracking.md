# Planning and tracking

Purpose: where work, decisions, evidence and plans live in the repo, and the rules that keep them trustworthy for teammates and for agents that start every session from zero.
Read when: adding or closing a task, recording a decision, writing a spec or design brief, deciding what to build next, or planning a week.

Templates: [todo](../../templates/todo.md), [task file](../../templates/task-file.md), [decisions log](../../templates/decisions-log.md), [decision record](../../templates/decision-record.md), [spec](../../templates/spec.md), [design brief](../../templates/design-brief.md), [production readiness checklist](../../templates/production-readiness-checklist.md).

## Where things live

| File | Holds | Never holds |
|---|---|---|
| `docs/todo.md` | Open actions and pending decisions, one row each | Long context, history |
| `docs/todo-archive.md` | Swept done rows, append-only | Edits to old rows |
| `docs/tasks/active/<slug>.md` | Multi-step work with a `## Status` section | Copies of the tracker row |
| `docs/tasks/someday/` | Parked ideas, not committed to | Dates |
| `docs/decisions.md` | Decisions: chosen what instead of what, and why | Plans, status |
| `docs/adr/YYYY-MM-DD-<slug>.md` | Big decisions with options and a review date | Small choices |
| `docs/specs/<slug>.md` | What a feature must do, now | "Previously we thought" |
| `docs/findings.md` | Measurements: date, version, sample size | Conclusions without data |
| `docs/feedback.md` | Raw user and tester feedback, verbatim | Paraphrases |

There is deliberately no "current state" document: the code, the tracker and the specs are the state. Permanent docs (specs, plans, task files) show only the current picture; history lives in git and in the decision log, which is the one intentionally historical file.

## 1. The tracker: docs/todo.md

- **Keep the tracker as a markdown file in the repo, not only in an issue tracker.** Why: it is diff-friendly, reviewed in the same PRs as the code, its status changes live in git history, and an agent reads it without API calls or tokens. Use the issue tracker for intake from outside (user bug reports, contributors) and link the issue from the row.
- **One `Active` table holds both actions and pending decisions:** `ID | Status | Action | Prio | Owner | Trigger | Due | Depends`. Why: most high-priority work waits on a decision, and two lists hide that dependency.
- **Owner says who must act for the row to move, independent of priority:** `AI` (buildable now), `@handle` (a teammate's hands or judgment), `PO` (a product decision), `design`, `external`. Why: priority says how important a row is, not whether it can start; `/next` uses Owner to find what an agent can do right now.
- **Status, not position.** Done is one move: the Status cell becomes `done YYYY-MM-DD`. A weekly sweep moves done rows and their details into the append-only archive. Why: moving rows between sections by hand loses them and causes merge conflicts between parallel branches.
- **A row that waits on an event gets a trigger, not a fake date and not a "WAIT" label.** Write it so it can be checked cheaply: "PR #41 merged", "signups > 50", "PO picks the pricing model". Why: "WAITING" forces someone to reopen the whole context, dateless rows never show up in a due list, and a trigger answers the next question immediately. The weekly [`/janitor`](../../skills/janitor/SKILL.md) checks triggers.
- **Use a due date only when something real happens on that date.** `YYYY-MM` means the end of that month.
- **Compute what is due with a script, never by eye:** `python .claude/skills/todo/scripts/todo_tool.py due`. Why: a model reading dates by eye takes the wrong date in a row for the due date and declares items due that aren't.
- **IDs are never recycled, carry a per-repo prefix (`APP-0042`), and the next one is computed from the working tree, the archive and every branch** (`todo_tool.py next-id`). Why: parallel sessions and teammates claim numbers on branches; a loose text search can match a note about the next ID instead of a real row, and a version or ID guard checks format, not uniqueness.
- **Check the table after every edit** (`todo_tool.py check`): eight cells per row, no `|` inside a cell, unique IDs, valid Status and Due.
- **Keep a curated "Critical path to <milestone>" plus an explicit "Not on this path" list.** "Open" means not done, not workable today. A row whose trigger is an external event is never offered as next. Why: without the exclusion list, `/next` keeps proposing work that can't start.
- **The agent updates the tracker without asking when** it finds an action that waits on a condition, when someone says "X is done", and when priority, trigger or due date change. Decisions are written into the row immediately, not at the end of the session. Why: unrecorded decisions come back as fresh questions next session.
- **Before implementing a row, fetch and check main and the open PRs.** Why: a parallel session or teammate may already have shipped it. Details: [git workflow](git-workflow.md).
- **Name rows in words when talking to people, with the ID next to it.** Why: "APP-0031" means nothing in a chat message.
- **Record follow-up work as rows, not as extra sessions or chat promises.**

## 2. Task files: docs/tasks/

- **Three folders with fixed meanings:** `active/` (in progress or next up), `someday/` (parked, not committed), `completed/` (done, solved elsewhere, or consciously dropped). Each folder's `README.md` has a `## Contents` list that changes in the same commit as any add, move or delete. Why: an index that skips an update lies (a folder listed as empty still holds files).
- **A big piece of work gets its own task file plus one tracker row that links to it;** the content is never duplicated.
- **Every active task file has a `## Status` section (current state and next steps), updated every time anyone touches the task.** Why: it is the only continuity between sessions and between teammates.
- **An item is self-contained:** what is wrong and why it matters, `file:line` references for every claim, whether the diagnosis is confirmed (reproduced) or a hypothesis, and the proposed fix including the test to add.
- **A close-note answers four questions:** what shipped (the mechanism, never just "fixed"), where (files, PR, version), how it was verified (test name, counter-test evidence), and what was consciously not done and why. Why: close-notes are re-read months later to answer "why is it like this?", and the "not done" line stops the idea being re-litigated.
- **When someone reports a task done, archive it right away;** don't wait for "please archive". Dropping a strategic item also gets a decision-log entry.

## 3. Decisions

- **Record every decision in `docs/decisions.md` the moment it is made:** what was chosen instead of what, the reason, who confirmed it. Append-only. Why: decisions made in conversation leave no trace in code, tasks or git, and months later either someone has to be asked or the agent guesses a reason and builds on it.
- **Before proposing a change to anything that looks decided, grep the decision log.** If it was decided, first say what was decided, when and why, and only then discuss, even when the product owner proposes the change. Why: settled debates otherwise come back every few weeks.
- **If you don't know why a filter, feature or exception exists, grep the log; if it isn't there, say "I don't know why".** Describe what it does; never invent why.
- **Write a decision record for big or hard-to-reverse decisions** (architecture, vendor, pricing, anything the team is torn about): context, options with pros and cons, the decision, what we knew at the time, and a review date. Why: reviewing outcomes against what was known is how the team gets better at deciding. Superseded records carry a banner naming their replacement; never build on a superseded one.
- **Never rewrite old entries in today's terminology.** They are a record, not the current state.
- **Don't widen a decision beyond what was said.** One "no" to one option is not a rule against the category; say the wider consequence out loud and ask. Why: a wrongly widened constraint silently deletes good options for months.
- **Don't ask for a decision nobody needs yet;** record it as a proposal with a trigger.
- **When a rule or spec changes:** add a decision entry, rewrite the spec to the new state (no "previously", no arrows), and shrink the tracker row to "done in vX.Y.Z" with a link.
- **Two ways to keep the log filled:** [`/decisions-mode`](../../skills/decisions-mode/SKILL.md) serves pending decisions one per message and records each answer; [`/decision-capture`](../../skills/decision-capture/SKILL.md) (optional, advanced) extracts confirmed decisions from agent transcripts nightly.

## 4. Evidence and metrics

- **Keep measurements in `docs/findings.md` with date, app version and sample size; keep raw feedback verbatim in `docs/feedback.md`.** Why: mixing evidence, decisions and plans makes all three unreliable.
- **Feed findings from tests, user testing and usage data back into the docs the same day.**
- **Propose only metrics with a lever:** name the decision the number would change before building a dashboard. Why: a number nobody can act on only makes someone feel bad.
- **Before deepening an analysis, check whether any realistic result would change a decision.** If none would, skip it.
- **Look at per-unit trajectories (per user, per day, per step of a funnel) before quoting an average.** Why: averages hide phase changes and bimodal behaviour, and the break point is usually the finding.
- **Reconcile a new metric reconstruction with the team's existing trusted number before presenting it;** if they disagree, present it as a draft. Why: an unreconciled query is guessing with decimals.
- **Keep metrics clean:** exclude the team's own and test accounts, reset the baseline before launch, count a session only after the first real interaction. Details on product telemetry: [engineering notes](engineering-notes.md).

## 5. Specs, plans and design

- **Spec before code for anything beyond a small fix. If the spec fits in one sentence, stop and write it out:** edge cases listed, and the why explainable to an agent six months from now. Why: an agent working for hours from a misread spec is the most expensive failure in AI-built products.
- **Look at options before steps.** For product and architecture questions, explore several angles first, then converge. For big decisions, describe the unconstrained ideal first, then cut it down to the MVP on purpose. Why: the MVP becomes a deliberate choice instead of a best guess.
- **Write the MVP as two lists, "IS in" and "is NOT in", plus the open questions to settle before building.**
- **Have the agent write the implementation plan and iterate on it before any code;** the plan ends with acceptance criteria as a checklist the agent checks against the running app. Why: the plan survives compaction, and new criteria surface in discussion that would otherwise overturn half-built code.
- **Concept before content:** propose two to four one-line concepts, let the product owner pick, then write the full version. Why: content written before a pick is wasted and harder to cut.
- **Prototype one hypothesis at a time, on its own branch or in its own repo.** Why: you get a clean answer and the main product takes no damage.
- **Gate each milestone on a human having used it and called it good, and write the gate into the plan.** Why: the agent can't judge usefulness or feel; work that moves past an unproven core loop is usually thrown away.
- **Write anti-goals as budgets, not bans** ("tests take at most 20% of the effort", "no new dependency without a reason in the PR"). Why: agents work around bans, so the banned work comes back in another form with no limit on it; a budget gives a number to check against.
- **Expect things to take twice as long and halve the scope;** set a launch date so polishing ends.
- **Design briefs state: goal, current behaviour verified live, who lands on the screen (every situation, including what must not be revealed), constraints, what to design, and what is out of scope.** Template: [design brief](../../templates/design-brief.md).
- **Markdown by default; HTML only when a diagram, mockup or option matrix is needed to understand the document.** Never HTML for rules, READMEs, trackers or agent instructions.
- **Mark the production-readiness checklist at the start of each larger feature (which items it touches) and again before the production deploy.** Open items are conscious decisions, not surprises.

## 6. Ideas: validate before building

- **Run every new product or feature idea through the 4-point test before any code:** sniff test, one written hypothesis, riskiest assumptions ranked by risk and cost to test, minimum success criteria on one metric. Use [`/validate-idea`](../../skills/validate-idea/SKILL.md). Why: building is the most expensive way to learn that nobody has the problem.
- **Test the riskiest assumption first, with the cheapest possible test** (a conversation, a landing page, a manual version).
- **In user interviews, ask about real past experiences, not hypotheticals.** Why: "would you use X?" produces polite estimates, not data.
- **Failed ideas are recorded with the reason and never deleted.** Why: the next "new" idea is often an old one, and the record saves a cycle.

## 7. Prioritizing and scheduling

- **Quick wins (15 minutes or less) first; then rank by fit with the current milestone; keep maintenance as a separate bucket.**
- **Items postponed three or more times get a forced decision: keep, scale down, postpone, or close** ([`/sink-test`](../../skills/sink-test/SKILL.md)). Why: silent re-dating hides the fact that nobody intends to do the item.
- **Schedule below capacity:** hard-book only part of focus time and keep the rest as buffer, split tasks over two hours, book only the first phase of research tasks, and compare estimates with actual time. Why: research tasks expand well beyond their estimate, and technical estimates are consistently off.
- **Raise a capacity concern at most once, without pressing.** If the team still wants to do it, proceed.
- **Do mechanical work end to end and report briefly; handle decision-heavy work one decision per message.** Why: decisions wear people out, mechanical work doesn't, and the real cost of a decision is reconstructing its context.
- **Keep a weekly rhythm:** janitor (archive done rows, check triggers), sink test, and a look at the critical path.

## 8. Skills for this workflow

| Skill | Use it to |
|---|---|
| [`/todo`](../../skills/todo/SKILL.md) | Add one row with a computed ID |
| [`/next`](../../skills/next/SKILL.md) | See the one next thing, or the full overview |
| [`/tasks`](../../skills/tasks/SKILL.md) | Create, park, complete or drop a task file |
| [`/work-log`](../../skills/work-log/SKILL.md) | Write self-contained items and evidence-backed close-notes |
| [`/note-this`](../../skills/note-this/SKILL.md) | Route one fact to the right file |
| [`/decisions-mode`](../../skills/decisions-mode/SKILL.md) | Clear pending decisions one per message |
| [`/janitor`](../../skills/janitor/SKILL.md) | Weekly sweep, trigger check, drop and stale candidates |
| [`/sink-test`](../../skills/sink-test/SKILL.md) | Force a decision on items that keep slipping |
| [`/validate-idea`](../../skills/validate-idea/SKILL.md) | 4-point test before building |
| [`/decision-capture`](../../skills/decision-capture/SKILL.md) | Optional: nightly decision extraction from transcripts |
