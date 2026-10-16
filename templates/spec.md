<!--
Feature spec / implementation plan. Copy to docs/specs/<slug>.md.
The agent drafts it; iterate with the product owner BEFORE any code. If the spec fits in one sentence, it is not done.
Present tense, current state only: when the spec changes, rewrite it and add a docs/decisions.md entry. No "previously".
Markdown by default; switch to HTML only if a diagram, mockup or option matrix is needed to understand it.
-->

# Spec: <feature>

Status: draft | agreed | building | shipped in vX.Y.Z | Tracker: APP-NNNN | Owner: <@handle>

## Problem

<Who has the problem, how we know (link findings/feedback), what happens today.>

## Goal

<One sentence: what the user can do afterwards that they can't do now.>

## Scope

**IS in:**
- <capability>

**Is NOT in:**
- <explicitly excluded, with why if it will come up>

## Behaviour

<User-visible behaviour, step by step. Name every state: empty, loading, error, success, no permission.>

### Edge cases

- Empty / missing data:
- Invalid or maximum-length input:
- Refresh or back button mid-flow:
- Second account (must not see the first account's data):
- Slow network, offline, double submit:
- Mobile viewport:

## Data and boundaries

<Entities and fields touched, who may read/write them, where identity comes from (server session only), external services called, personal data involved. Migration needed: yes/no.>

## Why it is built this way

<The reasoning an agent needs in six months so it doesn't "fix" a deliberate choice. Link decision entries.>

## Constraints and anti-goals

- Fixed: <stack, components to reuse, locales, performance limits>
- Agent's discretion: <internal structure, naming, libraries within the stack>
- Budgets: <e.g. "tests at most 20% of the effort", "no new dependency without a reason in the PR">

## Milestones and gates

- M1: <thin end-to-end slice>. Gate: <a human used it and called it good>. Do not continue past a failing gate.
- M2: ...

## Acceptance criteria

<!-- The agent checks each one against the running app before saying done, and lists deliberate deviations in the PR. -->
- [ ] <observable behaviour>
- [ ] <edge case>
- [ ] Docs and tests updated in the same PR
- [ ] Production-readiness items touched by this feature marked (templates/production-readiness-checklist.md)

## Open questions

- <question> - owner: <@handle or PO> - needed by: <milestone>

## Deviation log

<!-- Every deviation from this spec during implementation: one line here plus a decision entry if it changes behaviour. -->
