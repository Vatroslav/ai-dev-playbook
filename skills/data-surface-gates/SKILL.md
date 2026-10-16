---
name: data-surface-gates
description: Mandatory privacy and access gates for every new data surface - page, server action, API route, webhook branch, export or dashboard that returns or accepts user data. Use while designing and implementing such a surface and as self-review before the PR ("new endpoint", "add a page that shows", "expose this data", "add a webhook"); manual /data-surface-gates <surface> to audit an existing one. NOT a general security review (see docs/agent/security.md).
argument-hint: "[surface to audit]"
---

# Data surface gates

Apply these at implementation time, not as a retrofit. For each gate: apply it OR write why it doesn't apply. "Didn't think of it" is not an option.

Why: access bugs don't fail tests or crash anything. The page renders, the numbers look right, and someone sees data they shouldn't. Only an explicit checklist catches them before users do.

## Preflight

- The surface shows only public, non-user data -> `SKIP: no user data on this surface` (say so in the PR).
- Audit mode with no surface named -> ask which route/page/action to audit.

## Gates

1. **Authorization inside every server-side entry point.** Each route handler and server action checks session and permission itself. A server action is a public HTTP endpoint: a hidden button, a feature flag or a check in the page component protects nothing. Identity comes from the server-side session, never from the request body or query string (IDOR).

2. **Owner/tenant scoping in the data layer.** Every query is scoped to the caller through a data function that takes the owner id first and throws when it is missing. Shared or team data is a deliberate exception: decide explicitly whether shared rows count in each new aggregate, count or bulk action.

3. **Eligibility gate - server-side, BEFORE the expensive query.** If a user must meet a condition to see data (active subscription, completed onboarding, required role), check it on the server before fetching, through ONE shared helper (never re-implement the condition per surface). Fail closed: unknown or NULL -> gated. This applies to actions called after the first render too: gate the action, not only the page.

4. **Fail closed on ambiguous identity.** Two rows for one email, an unparseable eligibility date, a missing tenant -> throw, never bind to an arbitrary match.

5. **Minimum-group gate for aggregates - including every DERIVED number.** If you show aggregates about other people, apply the minimum group size in the aggregation layer (a sub-threshold row never exists, so the UI can't show it by accident); thresholds are configuration, not constants. For every number on screen ask: can one person's value, or the existence of a small group, be inferred from it or from the DIFFERENCE of two such numbers (facet totals, before/after)?

6. **Per-user throttle on every cache-bypassing call.** A "refresh" or poll that skips the cache lets the client alone set the pace on your most expensive query (denial of wallet). Throttle per user and degrade to the cached path.

7. **Webhook branch - full parity with existing branches.** Verify the signature; verify the referenced user/entity exists before upsert (if the provider disables webhooks on error responses, answer 200 and log a warning instead of 4xx); sanitise numeric fields (round, cap); upsert in try/catch; rate limit, anti-replay and body-size cap through the shared guard module.

8. **Out-of-order guard on client re-queries.** Successive requests (filters, polls) can resolve out of order. Use one monotonic request-sequence counter shared by ALL actions that write the same state, and apply a result only if it is still the latest.

9. **Nothing sensitive leaks sideways.** No user data in URLs or query strings, logs, error-tracker context or analytics events. Error responses are generic.

10. **Boundary guards still pass.** If the repo has static or CI guards on the data-access layer (allowed access modules, RLS checks), run them locally when you touched that chain.

## Output

Add a **"Gates"** section to the PR body:

```
## Gates
- [x] 1 Authorization: requireUser() in getReport action (src/actions/report.ts:12)
- [x] 2 Scoping: data.listReports(ownerId) (src/data/reports.ts:40)
- [ ] 5 Minimum group: n/a - surface shows only the caller's own rows
...
```

Applied gates link to code; non-applicable gates say why. Reviewer agents then get a checklist instead of hunting for holes.

## What NOT to do

- No gate enforced only in the UI.
- No threshold as a literal in a component.
- No "will add auth later" on a surface that merges to main.

## Project overrides (fill in)

- Session/guard helpers: `<requireUser / requireTenant / requireRole>`
- Minimum group size config key: `<MIN_GROUP_SIZE>`
- Shared webhook guard module: `<src/lib/webhook-guard.ts>`
- Boundary guard command: `<pnpm guard:data-access>`
