<!--
Design brief for one screen or flow, written for a designer or a design tool.
Copy to docs/specs/design-brief-<screen>.md. Final user-facing copy is approved by the product owner.
-->

# Design brief: <screen or flow>

Date: YYYY-MM-DD | For: <designer / design tool> | New screen or redesign | Tracker: APP-NNNN

**Goal:** <one sentence: what the user gets from this screen>

## 1. Today

<Current behaviour, verified live on <environment> on YYYY-MM-DD - not from memory or old screenshots. Link screenshots.>

## 2. Who lands here

| Situation | Who | Signed in | What they must see |
|---|---|---|---|
| <first visit from an invite link> | <new user> | no | <...> |
| <returning, no data yet> | <user> | yes | <empty state> |
| <no permission> | <member without role> | yes | <...> |

What the screen must NOT reveal in any situation (e.g. that an account or route exists, another user's data, internal flags):
- <...>

## 3. Given constraints

- Locales: <list>; every string in every locale
- One consistent form of address; no emojis in UI copy
- One way back from every state
- Components to reuse: <from DESIGN.md>
- Accessibility: contrast, focus order, colour never the only signal

## 4. What to design

- Shape: <layout idea; alternatives if unsure>
- Content: <elements, in priority order>
- Widths: desktop <px> and mobile 375 px
- States: empty, loading, error, success
- Browser tab title: <...>

## 5. Out of scope

- <explicit list>

## Handoff back

The implementation transcribes exact values from the design (sizes, weights, fills, copy word for word) before mapping to tokens, compares both side by side before "done", and lists every deviation in the PR ("Deviations from design: 0" is written out explicitly).
