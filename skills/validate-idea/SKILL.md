---
name: validate-idea
description: Run a new product, feature or side-project idea through the 4-point test (sniff test, hypothesis, riskiest assumptions, minimum success criteria) with seeded substitutes and channels and a mandatory web check of the riskiest assumption, then record the verdict in docs/ideas-validated.md. Use for "I have an idea for...", "validate this", "is this worth building?", "run it through the test". Builds nothing.
argument-hint: "[the idea in one or two sentences]"
---

# Validate idea

Kills bad ideas cheaply, before any code. Why: building is the most expensive way to find out that nobody has the problem, and an agent will happily build whatever it is asked to.

## Preflight

- No idea stated -> ask: "Describe the idea in one or two sentences: who has what problem?"
- Read `4-point-test.md` (next to this file) and follow its order; don't skip or reorder steps.
- Read `docs/ideas-validated.md` if it exists: don't validate the same idea twice, and check the new idea against ones that already failed (why did they fail, does it apply here?). Missing -> create it with the header `# Validated ideas` and the line "Verdicts from /validate-idea. Failed ideas are never deleted."

## Steps

1. **Sniff test** (instinct, no research): pain vs willingness to pay, team fit, sustainability, a visible path to validation, unfair advantages. A clear fail here -> verdict NO-GO, record, stop.
2. **Seeded substitutes and channels** (before choosing the riskiest assumption): generate three to five random strings with a script (`python -c "import secrets; [print(secrets.token_hex(6)) for _ in range(4)]"`). Each string picks one angle on the customer (who exactly, where they are, when the problem appears, what they use today, who already sells to them). From each angle derive one substitute the customer ALREADY uses and one channel that would really reach them. The seed changes the angle, not the facts: every item must be real and checkable by a web search. Why: unseeded lists always return the same generic substitutes and channels.
3. **Hypothesis:** one written, testable sentence in a template from `4-point-test.md`.
4. **Riskiest assumptions:** list them in order of risk (they have the problem; they care enough; they will pay or another monetization works; no good-enough substitute). Place each on risk x difficulty-to-test and pick the first to test. **Web search is mandatory for the riskiest one**; revenue or market numbers from listicles are unconfirmed until found at a primary source (a pricing page, marketplace rules, a public registry). Label anything unconfirmed as "unconfirmed".
5. **Minimum criteria for success:** costs (hours, money, opportunity cost) vs ONE reward metric with a threshold and a time window ("40 waitlist signups from 300 visitors in 3 weeks").
6. **Cheapest test of the riskiest assumption:** a conversation script, a landing page, a manual or fake-door version. Name what result would kill the idea.
7. **Record** in `docs/ideas-validated.md`:
   ```
   ### Validation: <idea> - NO-GO | FAILS | SURVIVES (YYYY-MM-DD)
   - Checked: <angles and sources reviewed; sources NOT reviewed>
   - Hypothesis: <...>
   - Riskiest assumption: <...> - <held / fell>, evidence: <links>
   - Success criterion: <metric, threshold, window>
   - Next step: <cheapest test, or why it stops here>
   ```
   Commit with an explicit path and the repo's PR flow.

## Boundaries

- Builds nothing, scaffolds nothing, and adds no tracker rows until the test passes AND the team explicitly confirms the direction.
- Never deletes or edits earlier verdicts; a re-validation is a new entry.
- No invented market sizes, user counts or "studies show".
