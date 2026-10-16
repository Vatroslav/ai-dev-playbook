---
name: release-note
description: Add a user-facing release note ("what's new") deterministically - material and version/date READ from git, draft in every locale per copy-voice, the product owner's "ok" in chat BEFORE any commit. Use when a user-visible change is about to reach production, or when asked to "add a release note", "write the changelog entry", "what's new for this release". NOT for the technical git history (conventional commits already are that) and NOT for tagging (see release / docs/agent/versioning.md).
---

# Release note

User-facing release notes are a curated projection of git history, written once. There is no hand-maintained CHANGELOG to keep in sync.

Why: notes written from memory list things users never saw (flags off in prod, fixes for bugs that never shipped), carry the wrong version or date, and slip onto staging before anyone approved the wording.

## Preflight

- No production tag exists yet -> use the first commit as the base and say so.
- Nothing between the tags is user-visible -> `SKIP: no user-visible changes since <old tag>`.
- The product owner is not reachable (headless) -> produce the draft only; never commit.

## Steps

1. **Material from git, not memory.** Between the previous and the new production tag (or the commit about to ship):
   ```bash
   git log --oneline <vOLD>..<vNEW or HEAD> | grep -E "^[0-9a-f]+ (feat|fix|perf)(\(|!|:)"
   ```
   Keep only what users actually experienced. Drop: changes behind flags that are off in production, admin tooling, infrastructure, analytics, and fixes for bugs that never existed in production (check the old tag's code).

2. **Version and date from git, never typed from memory.**
   ```bash
   git show <sha>:package.json | grep '"version"'
   git log -1 --format=%cs <sha>
   ```
   Use the commit where users could FIRST see the change (or the production tag for per-release notes).

3. **Draft.** One line per change; merge related commits into one self-contained sentence; say what changed and why it is better for the user, not how ("Pages load faster", not "added a 300 s cache"). Category: New / Improved / Fixed / Privacy. Suggest at most one highlight - editorial, the product owner decides. Write every required locale per copy-voice (natural, not literal).

4. **Print the full draft in chat and WAIT for "ok"** - every locale, category, highlight, version, date. Never "commit and look on staging". This applies to edits of existing notes too.

5. **After "ok":** add the entry at the top of the notes file; commit as `docs(release-notes): <version>` (no version bump); ship with feature-pr (the copy gate is already satisfied). For per-release notes, commit BEFORE the production deploy so the note ships in the same build; if the deploy slips, fix the date.

## Output (draft in chat)

```
Release note draft - v1.4.0 (YYYY-MM-DD, from git)
Highlight (suggested): <one entry or none>
[en]
- New: You can export your history as CSV.
- Fixed: Totals no longer change when you switch tabs.
[<second locale>]
- ...
Excluded: <commit> admin-only; <commit> flag off in prod
```

## What NOT to do

- No version read from the current working copy instead of `git show <sha>:...`.
- No draft shown only after it is already on staging.
- No recaps of existing features, no invented historical entries (forward-only, no backfill).
- No commit prefixes, ticket ids or implementation details in user-facing text.

## Project overrides (fill in)

- Notes file: `<src/content/release-notes.json>`
- Locales: `<en, ...>`
- Version file: `<package.json>`
- Tag pattern: `<vX.Y.Z>`
