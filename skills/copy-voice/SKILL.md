---
name: copy-voice
description: Voice, tone and rules for ALL user-visible text - UI strings in message catalogs, buttons, helper, error and empty states, emails, release notes, store listings. Load BEFORE writing or changing any user-visible string ("write the copy", "change this label", "error message for", "translate this screen"). This is a TEMPLATE - the team fills in its own voice once. NOT for internal admin-tool labels (list them in the PR instead).
---

# Copy and voice

The product speaks to the user - not the team behind it, not the developer, not the AI that wrote it.

Why: copy written by an agent drifts toward the same tells (hedging, empty value statements, balanced "on one hand" intros), invents features, and lands in one locale only. Users notice all three.

## Preflight

- The "Team voice" section below still has `<placeholders>` -> apply the generic rules, flag "voice not configured" in your reply, and ask the product owner to fill it in once.
- The change touches no user-visible string -> `SKIP: no user-facing copy`.

## Team voice (fill in once)

- Product voice in three adjectives: `<calm, clear, warm>`
- Form of address: `<informal "you" | formal>` - one form everywhere
- Person: `<no first person ("we") | "we" allowed in emails only>`
- Words we use: `<"workspace" not "account", ...>`
- Words we never use: `<dehumanising or internal terms, competitor names, ...>`
- Emojis: `<never | only in ...>`
- Required locales: `<en, ...>`

## Rules

- **Short.** Button = verb + object ("Export report"). Helper text: one or two sentences. No filler.
- **Active and direct.** No impersonal passive ("Your request has been received" -> "We got your request" or "Request sent", per the voice above).
- **Exact numbers, locale-formatted.** Dates, decimals, currency per locale conventions.
- **Never invent a feature, a number or a promise.** If unsure it exists, check the code or leave it open.
- **Errors say what happened and what to do next,** without blame and without internals ("Couldn't save. Check your connection and try again.").
- **Empty states explain what will appear and how to make it appear.**
- **Privacy-sensitive messages are calm and blame-free** ("Not enough data to show this chart yet") and never reveal individual users.
- **Don't assume user attributes the app doesn't collect** (gender, age, location). Use neutral phrasing.
- **Reproduce labels users chose verbatim** (option names, their own data); use the product's established vocabulary in public copy.

## Locales

- Every string goes into EVERY required catalog in the same change. A screen in only one required locale is not done.
- The second locale is natural, not a literal translation: ICU plurals, ordinals, number and date formats.
- Mechanically checkable rules are enforced by a catalog test (key parity, no empty strings, banned patterns, plurals through the real translator) - see `docs/agent/testing.md`.

## Anti-AI checklist

No "it is worth noting", "in that context", "keep in mind", "seamless", "unlock", "empower"; no balanced "on one hand / on the other hand" intros; no empty value statements ("helps you make better decisions") - say what the user concretely gets; no hedge stacking when the claim stands; vary sentence length.

## Release notes

Human, not technical; what changed and why it is better for the user; forward-only; category label. Procedure: release-note skill.

## Self-check before delivering copy

- [ ] all locales filled, keys in sync
- [ ] form of address consistent; no emojis unless the voice allows; no passive
- [ ] numbers exact and localised
- [ ] no AI phrasing, no invented features
- [ ] printed in chat (all locales) and approved BEFORE merge - the copy gate

## Output

A table in chat, one row per changed key:

```
| key | en | <locale 2> |
|---|---|---|
| export.button | Export report | ... |
```

Then wait for "ok" before the PR is armed (feature-pr, copy gate).
