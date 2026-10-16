# Decisions

What was chosen, instead of what, and why. Copy to `docs/decisions.md`.

- **Append-only.** This is the only document where history is intentional. Never rewrite an old entry in today's terms; a reversed decision gets a new entry that names the one it supersedes.
- **Write the entry the moment the decision is made**, in the same commit as the work it affects if there is one.
- **Grep here before saying "I don't know why"** and before proposing anything that may already have been decided or rejected. If it was decided, state what, when and why before discussing a change.
- **Only confirmed decisions.** An unconfirmed proposal, or silence after a long message, is not a decision. A misattributed decision is worse than a missing one.
- Big or hard-to-reverse decisions also get a record in `docs/adr/` (template: `templates/decision-record.md`); link it from the entry.
- Entries captured automatically by `/decision-capture` use the same format; review them and delete noise.

Format:

```
## YYYY-MM-DD

- **[YYYY-MM-DD]** <decision in one sentence: X instead of Y>
  Reason: <why, as stated>
  Confirmed by: <@handle> - "<short verbatim quote>" (<where: PR #N, meeting, session id>)
  Supersedes: <earlier entry date and title, or omit>
```

---

## YYYY-MM-DD

- **[YYYY-MM-DD]** Example: Postgres instead of SQLite for the main database
  Reason: we need row-level security for multi-tenant data from day one.
  Confirmed by: @handle - "Yes, Postgres, RLS is non-negotiable" (PR #3)
