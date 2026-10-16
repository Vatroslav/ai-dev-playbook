---
name: api-client
description: Conventions for code that calls a third-party REST API (payments, email, maps, auth providers, any SaaS) - one request wrapper with retries, backoff and token refresh, explicit success checks on writes, pagination that never returns partial data, a small exception hierarchy, caching of per-poll calls, plan/apply for bulk writes. Use whenever adding or changing an outbound API call or handling its errors ("integrate with X", "call the X API", "sync from X", "the X call fails sometimes"). Each rule guards against a quiet failure mode; do not simplify past them. NOT for routes your own server exposes (use backend-route-checklist).
---

# Third-party API clients

Why: integration bugs are quiet. A write that "succeeds" but does nothing, a list that silently stops at page 3, a poll loop that burns the rate limit - none of them crash, so tests and monitoring rarely catch them.

## Preflight

- The project already has a client module for this API -> extend it; never add a second one (grep for the base URL and the SDK import first).
- An official SDK exists -> prefer it for transport, but the rules below still apply around it (success checks, pagination, exceptions, caching).
- Credentials: read from env / secret manager in one module; the agent never reads or prints the values (`docs/agent/security.md`).

## 1. All HTTP goes through one request wrapper

One `request()` (with `get/post/put/delete` helpers) owns: base URL, auth header injection, token refresh on 401 (once), 429 handling with `Retry-After` (capped), exponential backoff on 502/503/504 and network errors, a timeout on every call. Never call the raw HTTP client elsewhere, and never stack extra sleep loops on top of the wrapper. Never retry other 4xx.

## 2. The wrapper's failure contract is explicit

Pick one and document it at the top of the module:
- returns `Response | None`, where `None` = network failed after all retries - then every caller checks `r is None` before reading the status; or
- raises `ApiError` after retries - then callers never see a half-failed response.

Guard bodies either way: some endpoints return an empty body on success (`data = r.json() if r.content else {}`).

## 3. Writes verify the status - never unconditional success

```python
r = await client.put(url, json=payload)
if r is None or r.status_code not in (200, 201, 202, 204):
    log.warning("[api] update_item failed (%s)", "network error" if r is None else f"HTTP {r.status_code}")
    return False
return True
```

An unconditional `return True` turns a failed write into a silent no-op that nobody notices. Call sites surface `False` to the user-facing log or UI; they don't swallow it.

Multi-step writes: if the first step fails, abort before changing anything the user can see. Once user-visible state has moved, always attempt to restore it, even if an intermediate step failed - never strand the user halfway.

## 4. Pagination raises on failure - never returns partial data

A failed page raises `ApiError("list_items failed at offset 200")`. Never `break` and return what you have: a partial list poisons diffs ("these 300 items were deleted upstream") and makes unfetched items look "never seen". Callers tell end-of-list from error: HTTP routes return 502, background jobs fail the whole run.

## 5. A small exception hierarchy

- `CredentialError` - missing/invalid credentials or config. The worker stops CLEANLY and waits for a human to reconnect; the supervisor must not restart it in a loop.
- `ReauthRequiredError(CredentialError)` - the refresh token is dead (`invalid_grant`). Clear the stored tokens and set a "reauth required" flag so the dead token is never retried.
- `ApiError` - non-auth failure after retries (network exhausted, 5xx, unexpected status). Include the operation and status, never the token or full payload.

## 6. Per-poll calls are cached

Anything the UI or a worker calls every few seconds must not hit the API per tick: cache keyed by entity id, refresh when the entity changes, write-through on user actions so the UI doesn't flip back to a stale value. Why: without a cache, every open tab spends the rate limit on calls that return the same answer.

## 7. Bulk or risky writes: plan, then apply

For anything that changes many records or goes live immediately: a read-only **plan** step produces a JSON plan plus a human-readable diff; the **apply** step re-fetches, re-checks that the plan still matches reality (drift guard, idempotency), and writes. Use separate read and write tokens with distinct scopes where the provider allows it.

## 8. External gotchas

- Never hardcode or default to IDs the platform may restrict for your app tier or region (they 404); surface the 404 with context.
- Module logger with a prefix (`[api]`); check which log levels actually reach production logs - an INFO line may be invisible there.
- Respect `Retry-After` in user-facing errors too ("rate limited, retry in 30 s").
- Webhooks from the provider: verify signatures and dedupe by event id (see data-surface-gates, webhook branch).

## Tests

- Unit tests mock at the wrapper boundary (`respx`, `pytest-httpx`, `msw`, `nock`); no live calls and no keys in CI.
- Test each failure path: 401 -> refresh -> retry once; 429 with `Retry-After`; page 2 of 3 fails -> raises; write returns 500 -> `False`/raise; empty body.
- One optional integration test against the real API lives in `tests/integration` and skips only when its credentials are completely absent (fails when half-configured).

## Output

When you add or change a call, state in the PR: which wrapper it uses, its failure contract, retry policy, and which of rules 3-7 apply.

## What NOT to do

- No raw `fetch`/`requests`/`httpx` call outside the wrapper.
- No `except Exception: pass` around API calls.
- No partial lists returned from a failed pagination.
- No tokens in logs, errors, URLs or commit messages.

## Project overrides (fill in)

- Client module: `<src/integrations/<provider>/client.ts>`
- Failure contract: `<returns null | raises ApiError>`
- Retry policy: `<max 3 attempts, backoff 1/2/4 s, Retry-After capped at 60 s>`
- Log prefix: `<[provider]>`
