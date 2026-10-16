<!--
Verification stamp for any file that makes claims about an external system
(repo settings, CI behaviour, a vendor's API, cloud config, DB schema, store rules).
Paste the YAML block at the top of that file (in SKILL.md files, nest it under `metadata:`).
-->

```yaml
---
verified:
  - by: agent/<model>            # or human:<@handle>
    at: YYYY-MM-DDTHH:MM:SS+00:00
    how: >-
      The live, read-only check performed, e.g.
      "gh api repos/OWNER/REPO/rulesets/123 -> required check 'check' present, bypass list empty".
    not_verified: >-
      Claims in this file that the check above did not cover (or omit).
stale_after: YYYY-MM-DDT00:00:00+00:00
---
```

## Rules

- **Write the stamp only after a live, read-only check** (API GET, `gh api`, `curl`, schema query, `--dry-run`), in the same commit as the claim it covers. **Reading a note, a doc or an old task is not verification** and is never stamped.
- **Only files with claims about external systems get the stamp.** Code, plans and decisions don't.
- **Set `stale_after` by how fast that system changes:** days for a vendor's beta API or pricing page, weeks for CI and repo settings, months for stable infrastructure.
- **Append a new `verified` entry on each re-check;** keep the old ones (they show how often the claim held).
- **List what was not verified.** A partial check stamped as complete is worse than no stamp.
- **A file past `stale_after`, or edited after its last `verified.at`, is a note, not a fact:** say "per <file>, verified <date>, not re-checked" or re-check before relying on it.
- **Optional automation:** a session-start hook that lists files past `stale_after` or modified after their last verification (see `docs/agent/security.md` for hook rules; such a hook lives where changes need review).
