<!--
Production-readiness checklist and human quality gate.
Use it twice per larger feature: at the START (mark which items the feature touches) and BEFORE the production deploy
(mark each touched item). Copy the relevant part into the spec or the PR description.
Marks: [x] solved | [~] minimal, consciously | [ ] open - an open item is a conscious decision with an owner, never a surprise.
-->

# Production readiness: <feature or release>

Date: YYYY-MM-DD | Version: vX.Y.Z | Reviewed by: <@handle>

## Human quality gate (scaled by risk)

| Change type | Gate |
|---|---|
| Trivial (copy, colour, layout tweak) | Look at the outcome in the browser |
| Medium (new form, endpoint, filter) | Spec gate + outcome gate |
| High stakes (auth, payments, schema migration, personal data, security headers) | Spec + outcome + review by a different model + this checklist + small beta group for major releases |
| Always | Structural gates: CI, lint, types, tests, monitoring |

- **Spec gate:** the spec is more than one sentence, edge cases are listed, and the "why" is written down.
- **Outcome gate:** run the smoke test; happy path; edge cases (empty, wrong input, maximum length, refresh mid-flow, back button); numbers cross-checked against the source; **again with a second account** (catches access-control bugs); mobile viewport.
- **Red flag:** "I believe it works because the agent said so." An agent's status report is a proposal, not a fact.
- **Pre-deploy question:** "What can go wrong here, and how would we know?" If the answer is "we don't know", the gate has not passed: add monitoring or a rollback plan first.

## Checklist

### Auth and access
- [ ] Authentication on every route and server action (checked in the handler, not only in the UI)
- [ ] Authorization before data access; identity from the server session only
- [ ] Data isolation between users/tenants enforced in more than one layer (app + database policy)
- [ ] Tested with a second account

### Payments (if any)
- [ ] Provider integration in test mode end to end
- [ ] Billing logic and subscription states, including failed payment, cancel, refund
- [ ] Webhooks verified (signature) and idempotent

### Data
- [ ] Consistent create/update/delete, including partial failures
- [ ] Idempotency for retries (webhooks, payments, double submit)
- [ ] Retention and deletion on request, across every place the data is stored
- [ ] Migrations dry-run; backward compatible with the running version during deploy

### Performance and cost
- [ ] No N+1 queries on main pages; indexes for new query patterns
- [ ] Health check endpoint reports version/SHA
- [ ] Cloud cost monitoring and a budget alert

### Operations
- [ ] Structured logging without personal data or secrets
- [ ] Error reporting armed and verified (a test error arrives)
- [ ] Alerting reaches a human who will act
- [ ] Runbook for the likely incidents
- [ ] Backup exists AND a restore was tested (know your recovery time)
- [ ] A support channel users can reach

### Security and compliance
- [ ] Secrets in a secret manager or CI secrets, never in the repo
- [ ] Rate limiting on auth and public write endpoints
- [ ] Security headers (CSP, HSTS, nosniff), and you know which routes CSP does not cover
- [ ] Privacy policy and cookie consent match what the app actually collects and which vendors receive data
- [ ] Data processing agreements with vendors that receive personal data
- [ ] Security review done before deploy

### Delivery
- [ ] CI green on the exact commit being deployed; CI builds the deploy artifact
- [ ] Dev, staging and production behave the same (config parity)
- [ ] Rollback possible in under 5 minutes, and someone knows how
- [ ] Feature flag or kill switch for risky features
- [ ] Meaningful tests for the risky paths; docs and runbooks updated

### Product
- [ ] Funnel events for the feature exist and exclude team/test accounts
- [ ] Accessibility basics (keyboard, contrast, labels)
- [ ] Supported browsers/devices checked (at least one non-Chromium browser)

### Strategic
- [ ] Vendor lock-in known; an exit path exists for each critical vendor

## Open items (conscious decisions)

| Item | Why it's open | Owner | Revisit when |
|---|---|---|---|
| | | | |
