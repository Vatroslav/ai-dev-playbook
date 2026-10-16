<!--
Task file. Copy to docs/tasks/active/<kebab-slug>.md (use the words the team already uses for the topic).
Add it to docs/tasks/active/README.md "## Contents" in the same commit, and add ONE row to docs/todo.md that links here.
-->

# <Task title in plain words>

Created: YYYY-MM-DD | Owner: <@handle or AI> | Tracker: APP-NNNN

## Goal

<One or two sentences: what is true when this is done, and why it matters to users or the team.>

## Context

<What prompted it. Links to spec, decision entries, issues. Facts with file:line references; mark each diagnosis as **confirmed** (reproduced) or **hypothesis**.>

## Plan

1. <step>
2. <step>

Acceptance criteria (checked against the running app, not the code):
- [ ] <observable behaviour>
- [ ] <edge case: empty / wrong input / refresh mid-flow / second account>

Watch out for:
- <known trap, with why>

## Status

<!-- Update on EVERY touch. This section is the only continuity between sessions and teammates. -->
**YYYY-MM-DD:** <current state in one or two lines>.
Next: <the next concrete step>.
Blocked by: <trigger or "-">.

## Close-note

<!-- Fill when done, then move the file to docs/tasks/completed/ and update both README indexes. -->
_DONE YYYY-MM-DD (vX.Y.Z):_ <what shipped - the mechanism, not just "fixed">. Where: <files, PR #N>. Verified: <test name, counter-test evidence, live check>. Consciously NOT done: <what and why>.
