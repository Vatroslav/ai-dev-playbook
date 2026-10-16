<!--
Playbook for N similar units (pages, modules, endpoints, screens) that need the same fix.
Process:
1. Do the FIRST unit slowly, with the agent, by hand. Verify it properly.
2. Have the agent fill in this file from that work: docs/playbooks/<name>.md.
3. Start a FRESH session: "Apply docs/playbooks/<name>.md to the remaining units, as a checklist. Do not rediscover."
   Optionally fan out: one subagent per batch of units, each given this file.
4. After each unit, tick it in the progress table. When a unit doesn't fit the playbook, stop and update the playbook first.
Why: without a playbook the agent rediscovers the problem N times and drifts by the sixth unit.
-->

# Playbook: <name>

Created: YYYY-MM-DD from unit `<first unit>` (PR #N) | Tracker: APP-NNNN

## The issue

<What is wrong, in one paragraph, and how it shows up for users.>

## Cause in our code

<The actual mechanism, with file:line references from the first unit.>

## Files to touch per unit

- `<path pattern>` - <what changes>
- `<path pattern>` - <what changes>

## Steps per unit

1. <exact step>
2. <exact step>
3. Run: `<command>` - expect <result>.

## How to verify a unit

- `<command or check>` - expect <measured value / 0 errors / visible state>.
- Before/after numbers go into the commit message.

## Do NOT repeat

- <trap hit on the first unit, with why>
- <tempting shortcut that breaks something>

## Out of scope

- <related problems seen along the way: add a tracker row, don't fix them here>

## Progress

| Unit | Status | PR | Verified (measured) |
|---|---|---|---|
| <first unit> | done | #N | <before -> after> |
| <unit 2> | open | | |
