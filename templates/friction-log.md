# Friction log

Where a human had to correct the agent, so recurring patterns become visible instead of depending on who remembers. Copy to `docs/agent/friction-log.md`.

- **How it's filled:** `/friction-scan` runs `friction_scan.py`, which extracts candidates deterministically from each developer's local transcripts (interrupts, rejected tool calls, follow-up prompts). The agent classifies them and appends the real ones here. The script never writes here.
- **What this log is NOT:** proof. Classification is model-based and makes mistakes. The log is for prioritization; promoting a pattern into a rule goes through `/evolve` with a human yes per item, never automatically.
- **Privacy:** a one-line summary and a type. Never quotes, customer or user names, numbers from data, or secrets.
- **Format:** `date | repo | skill | type | description`. Types: `context` (claimed without reading available context), `invented` (fabricated specific), `scope` (did more or other than asked), `bug` (shipped broken code), `copy` (wording rejected), `overload` (too much at once), `omission` (skipped a required step), `process` (git, tracker or handoff rule broken).

## Recurring patterns

Update when a type appears three or more times. This is the part people read.

| Pattern | Count | Status | Next step |
|---|---|---|---|
| Claim about architecture or data without reading the available context | 3 | Rule exists - being broken, not missing | Escalate: checklist in the relevant skill |
| Too much information in one reply | 2 | Watching | - |

Status values: `Rule missing` (propose one via /evolve) | `Rule exists - being broken` (needs a stronger mechanism, not another rule) | `Fixed` (date and what fixed it) | `Watching`.

## Findings

### YYYY-MM-DD - run N (sample: N candidates reviewed, M real)

- YYYY-MM-DD | web-app | - | context | Claimed a table feeds the dashboard; the dashboard reads a different view. Architecture claim without checking.
- YYYY-MM-DD | web-app | todo | process | Added a tracker row by hand with a recycled ID.
