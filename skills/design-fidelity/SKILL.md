---
name: design-fidelity
description: Port a design handoff (HTML/CSS prototype, design-tool export, tokens, screenshot spec) into code by transcribing exact values instead of approximating, rendering both side by side before commit, and listing every deviation in the PR. Load BEFORE porting any handoff element ("build this screen from the design", "implement the mockup", "match the prototype"). NOT for UI work with no handoff (follow the design tokens file).
---

# Design fidelity - transcribe, don't approximate

## Why this is structural, not a reminder

The typical miss: elements get recreated "from memory" or "by meaning" instead of copying exact values, and nobody flags the deviation. A written reminder gives way under pressure. So this skill has two concrete steps and an objective gate.

## Preflight

- No handoff artifact available (only a verbal description) -> `SKIP: no handoff to transcribe - use the design tokens file and ask for a mockup if fidelity matters`.
- Several versions of the handoff exist -> the prototype beats the README, and a newer screenshot beats an older handoff. Diff the variants and say which one you used.

## 1. Transcription first (while writing)

1. Open the handoff CSS/HTML for that element BEFORE writing code.
2. Copy exact values, no remembering, no guessing:
   - dimensions: font-size, line-height, height, padding, radius, gap;
   - colour and fill: solid vs transparent, which token, opacity;
   - typography: font-weight, letter-spacing, text-transform;
   - copy, verbatim;
   - formatter options (month "long" vs "short", decimals, currency display).
3. Only then map to the repo's tokens. The token name may change; the look may not.
4. In doubt, grep the prototype. Don't assume.
5. Use semantic names in code (`PlanCardCompact`), never design shorthand ("variant B").

Embellishments not in the prototype (extra icons, arrows, glow, shadows) and paraphrased copy are silent infidelities - forbidden without explicit mention.

## 2. Visual diff before commit (objective gate)

1. Render the handoff prototype. It is the source of truth for look and copy.
2. Render the live component (dev server; behind login -> a temporary auth-free preview route, deleted before commit).
3. Screenshot both at the same viewport and compare side by side: fill, case, dimensions, typography, spacing, copy. Check desktop and a 375 px mobile width.
4. For each difference: align with the handoff, or keep it consciously and list it.

If screenshots are unreliable in your preview tool, compare computed styles (`getComputedStyle`) for the transcribed properties instead, and say the visual judgement is still the human's.

## 3. Deviations list in the PR (mandatory)

Add a section **"Deviations from handoff"**. An empty list is not allowed implicitly; if there are none, write:

`Deviations from handoff: 0 (transcribed 1:1, visual diff clean)`

Each deviation: WHAT differs + WHY (technical constraint, conscious decision, waiting for the product owner -> link to the task). "Close enough" is not a reason.

## Edge cases

- A handoff value conflicts with a functional constraint (e.g. a label string is also a lookup key): keep the function, open a task for a display-only variant, list the deviation.
- Prototype animation or interaction not ported in this phase: list what was omitted.
- A control repeated across screens: build one shared component, not one per screen.

## What NOT to do

- No "inspired by" implementations.
- No leftover preview routes or auth bypasses in the commit.
- No silent copy edits - copy changes go through the copy gate (see copy-voice).

## Project overrides (fill in)

- Handoff location: `<docs/design/handoffs/>`
- Design tokens file: `<DESIGN.md or src/styles/tokens.css>`
- Preview route pattern: `<app/(preview)/...>` (must be deleted before commit)
