---
name: thinking-partner
description: Structured sparring for product, technical or team decisions - frames the decision, widens the option space with seeded lenses, runs two or three fitting mental models (inversion, second-order effects, pre-mortem, reversibility...), stress-tests with an isolated critic, and ends with the deciding variables and the cheapest next test. Use when someone explicitly asks "help me think through X", "what am I missing", "stress-test this idea", "pre-mortem this", "second-order effects", or names a mental model. NOT for a casual "what do you think" and NOT for a quick reality check - use /strict-mode.
argument-hint: "[the decision or problem]"
---

# Thinking partner

Helps the team think, not decide for them. Why: agents converge on the options people walked in with and answer in generic advice; deliberate divergence and named models surface the option or risk nobody raised.

## Preflight

- No decision or problem stated -> ask one question: "What are you deciding, and by when?"
- The question is a factual lookup -> answer it directly; this skill is the wrong tool.

## Steps

1. **Frame (one short block):** what exactly is being decided; by when; what is fixed (budget, deadline, stack, people); what "good" looks like. If one of these is missing and matters, ask ONE question, then continue.
2. **Load context from the repo, not from the human:** `docs/decisions*.md` and `docs/adr/` (don't re-propose rejected options without a new argument; treat decided things as given), `docs/todo.md`, `docs/findings.md`, the relevant spec. Numbers only if read or measured; estimates labelled with their inputs.
3. **Diverge with seeded lenses.** Generate three to five random strings with a script (`python -c "import secrets; [print(secrets.token_hex(6)) for _ in range(4)]"`). Map each string to one lens (by its first character, or in order): who benefits, time horizon, resource spent, what is given up, who is harmed, what a competitor would do. From each lens derive one option. Options must differ in kind, not in degree, and stay plausible for this team. Why seeded: unseeded brainstorming returns the same generic options every time.
4. **Run two or three mental models that fit the problem type** (catalog and fit table in `models.md`). For each: one paragraph of what it reveals here, concretely. Never run a model just to show it.
5. **Outsider test:** give the leading option, the frame block and the question to a fresh critic subagent (the `/isolated-critic` skill if the repo has it). It sees nothing else. Fold its strongest objection into the analysis.
6. **Converge, without deciding for them:**
   - the two or three variables that actually decide this;
   - each serious option with its main trade-off and its reversal cost;
   - your leaning, labelled as such, with the assumption that would flip it;
   - the cheapest test that would reduce the biggest uncertainty this week.

## Output

```
**Deciding:** <one sentence> by <when>. Fixed: <constraints>.
**Options:** (from the lenses, differing in kind)
1. <option> - trade-off: <...> - reversal cost: <...>
2. ...
**What the models show:**
- <model>: <what it reveals here>
**Critic's strongest objection:** <one or two lines>
**Deciding variables:** <2-3>
**My leaning:** <option> - flips if <assumption> is wrong. (Your call.)
**Cheapest next test:** <what, how long, what result would change the decision>
```

Offer to record the outcome in `docs/decisions.md` once the human decides; never record a leaning as a decision.

## Boundaries

- At most one clarifying question per message.
- No generic advice: a recommendation that would fit any team is not one.
- No invented numbers, market sizes or "studies show".
- Writes nothing to the repo unless asked.
