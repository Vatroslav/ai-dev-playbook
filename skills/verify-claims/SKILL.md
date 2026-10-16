---
name: verify-claims
description: Audit every factual claim in the agent's last message - check each against the web or official docs, the actual files in the repo, or by redoing the computation - and report Verified / Incorrect / Cannot verify with sources. User-invoked - /verify-claims, "verify that", "are you sure?", "check your last answer".
disable-model-invocation: true
argument-hint: "[optional: one specific claim to check]"
---

# Verify claims

Re-checks the last message claim by claim instead of defending it. Why: a plausible wrong answer costs more than a lookup, and arithmetic done "in your head" is the most often missed error.

## Step 1: list the claims

List every factual claim in your last message and classify it:
1. **External world** - API behaviour, library features, versions, limits, prices, statistics -> web search or the official docs; go to the primary source (docs, changelog, pricing page), not a blog.
2. **Repo or files** - file contents, config values, dates, numbers from docs -> find the file and read it in full; don't rely on memory of having read it.
3. **Live system state** - what is deployed, a setting, a schema -> a read-only check (`curl`, `gh api`, a schema query). A repo note is not proof.
4. **Computation** - totals, percentages, conversions, date math -> redo it step by step, with a script for anything non-trivial.
5. **Mixed** - split it and verify each part.

With an argument, check only that claim (and anything it depends on).

## Step 2: no factual claims?

Say so plainly: "The last message contains no factual claims to verify - only a proposal / opinion / plan." Don't invent verification.

## Step 3: verify and report, per claim

- **Verified** - the claim + source (URL, or `file:line`, or the command and its output).
- **Incorrect** - what was wrong, what is right, source.
- **Cannot verify** - why (no public source, file missing, ambiguous wording, no access), and what would settle it.

Then one line: what changes in the original answer because of the incorrect claims, with the corrected answer if it changes.

## Step 4: systemic errors

Only for a pattern (an invented API, a misread repo structure, a derived number presented as measured), offer: "This is a pattern: <cause>. Record it as feedback?" If yes, write it with the feedback template (Why / How to apply / Principle). Not for one-off typos.

## Rules

- Don't skip a claim because you feel sure.
- When the source contradicts the message, say so without softening ("I may have been partly right" is not allowed if the source says otherwise).
- Always re-run numbers computed without a tool.
- Never mark something Verified based on a note, memory or your earlier message.
