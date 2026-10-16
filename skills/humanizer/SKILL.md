---
name: humanizer
description: Detects AI writing patterns in a draft and rewrites it in a natural voice for its real context (medium, task, reader). Use on /humanizer, "make it not sound like AI", "clean this up", "polish this draft", and before showing any outward-facing draft - emails, release notes, landing copy, blog or social posts, PR descriptions read by outsiders, docs for users. NOT for specs, SQL, code comments or agent instructions.
argument-hint: "[text or file path]"
---

# Humanizer

Rewrites text so it fits its real context. Text that fits its context reads as human as a side effect. Why: readers who spot generated text stop trusting the product or the person who sent it, and one invented detail exposes the whole message.

Do NOT optimize for "sounding human" or for fooling AI detectors; both produce worse writing.

Credit: several patterns in the hit list and the draft / what-still-sounds-generated / final process follow Siqi Chen's [humanizer](https://github.com/blader/humanizer) skill (MIT License, Copyright (c) 2025 Siqi Chen; see [NOTICE](../../NOTICE.md)), which is based on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide.

## Preflight

- No text and no readable file path -> `SKIP: give me the text or a file path`.
- Text is a spec, SQL, code, a code comment or agent instructions -> `SKIP: out of scope - humanizer is for text people read as communication`.

## Voice anchor

For external text, read the team's voice guide first if it exists (`docs/voice.md` or the copy rules in `DESIGN.md`). If the user gives a sample of their own writing ("this is how I write"), match its rhythm, vocabulary and habits instead.

## Precedence when rules collide

1. Truth, safety, accessibility, legal and platform requirements
2. Explicit instructions from the user
3. Norms of the genre and medium (an email is not a landing page is not a technical doc)
4. The hit list and specificity rules below
5. The optional watch list

If the user wants bullets, give bullets. Don't flatten useful structure for style.

## Not AI tells by themselves

A dash, a semicolon, a colon, a well-formed paragraph, "however" doing real work, the precise word. The problem is the same move repeated, not any single move. Never overcorrect: no deliberate typos, broken grammar, inserted slang, fake hedging, manufactured casualness or randomized sentence lengths.

## Specificity discipline

- Fewer verified facts beat more assumed ones. No invented milestones, quotes, user counts, or "over 5,000" without a source.
- Don't narrate internal mechanisms or motives as fact when the reader can't check them.
- No "experts say", "research shows", "many users report" padding.
- Causal claims need a source; otherwise write "followed" or "coincided with". Exact quotes, metrics and promises about the future are fragile: attribute them, soften them, or delete them.

## Hit list

1. **Inflated significance** - "revolutionary", "powerful", "seamless", "robust" (unless it means fault-tolerant), "game-changing". Say what it does: "exports your data as CSV".
2. **Sycophantic or cheerleading openers** - "Great question!", "Absolutely!". Start with the answer.
3. **Stacked hedges** - at most one qualifier per sentence.
4. **Empty transitions** - "Furthermore", "Moreover", "It's worth noting", "In conclusion", "Let's dive in". Let the next sentence carry the link.
5. **Lists where prose belongs** - lists are for steps, comparable items and reference. Not for one idea split into three bullets or for two items.
6. **Buzzwords** - leverage, utilize, synergy, ecosystem, holistic, stakeholders, best practices. Use the plain word or name the actual thing or person.
7. **Filler phrases** - "in order to" -> to; "due to the fact that" -> because; "has the ability to" -> can; "make sure to do X" -> do X.
8. **Missing actor** - "The settings should be updated" -> "Update the settings" or "We updated the settings".
9. **Enthusiasm mismatch** - a bug fix is not an exciting new feature.
10. **"Serves as / stands as / represents"** -> "is", "shows".
11. **Generic gravitas** - "in today's fast-paced world", "at the heart of what we do". Replace with something concrete or delete.
12. **"It's important to note that"** - let the claim stand.
13. **The same connective dash in every paragraph** - use a period, a comma or a connective that names the relationship.

## Concrete anchor per paragraph

Every substantial paragraph needs at least one of: a specific number with meaning, a named product feature or place, a direct quote, a concrete decision or moment, a checkable detail. "Many", "various", "in meaningful ways" don't count.

## Watch for regularity

Generated text gets suspicious when its most visible feature is its own regularity: every list has three items, every paragraph follows claim-then-elaboration, "not X but Y" rhythm, the same closing line shape, a recurring metaphor. Break a pattern where it dominates; don't randomize.

## Process (two passes)

1. Read the voice anchor (external text) and the input.
2. Mark hit-list patterns and unearned specifics (unsourced numbers, quotes nobody said, invented details): attribute, soften or delete them.
3. Check the concrete anchor per paragraph.
4. Draft the rewrite: active verbs, the actor named, short sentences where they help, joined sentences where ideas are tightly linked.
5. Self-audit: "What still sounds generated?" Check regularity: any pattern three or more times, or dominating two consecutive paragraphs, gets at least one occurrence rewritten.
6. Anti-overcorrection check: did I add fake human moves? Remove them.
7. Final rewrite. If the text is in another language and a language-specific style check exists for it, run that after this pass, never before.

## Output

```
**Draft:**
...

**What still sounds generated:**
- ...

**Final:**
...
```

Skip the first two sections if the user only wants the final text.

## When to bend the rules

Marketing copy that explicitly wants punch: loosen, but still no sycophancy, stacked hedges or invented numbers. Technical accuracy always wins over style.

Final test: "Would a person write this without thinking about it?" If not, rewrite it, without adding fake human moves.

Optional: keep `examples.md` next to this file with two or three before/after pairs from the team's own drafts, each with its "what sounds generated" list, and calibrate on them.
