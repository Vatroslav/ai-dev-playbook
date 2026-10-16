<!--
Decision record (ADR) for big or hard-to-reverse decisions: architecture, vendor, pricing, data model,
anything the team is torn about (those are the most useful to review later).
Copy to docs/adr/YYYY-MM-DD-<short-slug>.md and add a one-line entry to docs/decisions.md that links here.
Review weekly (this week's records), monthly (outcomes of older ones), and at the review date below.
If this record is later replaced, add the banner at the top; never build on a superseded record.
-->

<!-- > **SUPERSEDED by docs/adr/YYYY-MM-DD-<slug>.md on YYYY-MM-DD.** Do not build on this record. -->

# <Short decision title>

**Date:** YYYY-MM-DD
**Status:** proposed | decided | implemented | superseded
**Category:** product | tech | data | security | money | team
**Deciders:** <@handles>

## Context

What is happening, and why is this a decision now? What breaks or stays blocked if we don't decide?

## Options

1. **Option A** - <description>
   - Pro:
   - Con:
   - Reversal cost: <what it takes to undo this later>
2. **Option B** - <description>
   - Pro:
   - Con:
   - Reversal cost:
3. **Do nothing / defer** - <what that means concretely>

## Decision

What we chose and why, in two or three sentences. Name the deciding variables.

## What we knew at the time

Key information we had, and what we did not have (unknowns, unverified assumptions, numbers that were estimates and their inputs).

## Consequences

What this commits us to, what it rules out, and what we must now build, monitor or document.

## Review

**Review date:** YYYY-MM-DD (or trigger: "<condition>")
**Outcome:** <fill in later>
**Would we decide the same?** <fill in later, with why>

<!--
Variant for changes to agent rules (a rule that keeps failing), replace Options/Decision with:
## What was already tried (date, change, result)
## Research (measured frequency, base rate vs the suspected cause)
## Diagnosis (generation habit vs knowledge gap, conflict with another rule, rule buried in a long file)
## Options (each with cost of failure vs cost of enforcement)
## Decision and implementation
## Open (expected effect; what triggers a revisit, e.g. "still frequent in 2 weeks -> move to a hook")
-->
