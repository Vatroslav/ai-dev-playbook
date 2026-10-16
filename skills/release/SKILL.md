---
name: release
description: Finalize a tested feature branch in a repo WITHOUT auto-merge-to-staging - sync with main and confirm nothing was lost, close the work-log item, merge the PR, deploy main, then create the git tag and GitHub release together for the version that is actually live, and delete the merged branch. Use when the human says "release it", "cut the release", "merge and release". NOT for the normal auto-merge flow (use feature-pr) and NOT for deploying during iteration (use deploy-vps or deploy-static).
disable-model-invocation: true
argument-hint: "[branch]"
---

# Release a finished change

Follow the order exactly. The version was already bumped in the behaviour-changing commit; releasing does NOT touch it.

Why: each step guards a known failure - a conflict resolution can silently drop code, a missed bump forces a fixup commit on main, and a tag without a release (or the reverse) drifts until nobody knows which number is live.

## Preflight

- On `main` -> `SKIP: release runs from a feature branch`.
- Not verified (no test evidence, not deployed to a test environment, no explicit human approval) -> stop and say what is missing.
- The version file does not hold the final number, or a source change has no bump -> fix it on the branch first (see `docs/agent/versioning.md`).
- `gh auth status` fails -> `SKIP: GitHub CLI not authenticated`.

## Steps

1. **Sync with main.**
   ```bash
   git fetch origin
   git log HEAD..origin/main --oneline
   ```
   If main moved: merge `origin/main` INTO the branch and resolve conflicts here, not in the PR UI. Then verify nothing was lost:
   ```bash
   git diff origin/main...HEAD --stat
   ```
   Every intended change must still be present. Re-run the tests after a conflict resolution.

2. **Work log.** Close the item on this branch with version and (after step 3) PR number - work-log skill. Docs-only commit, `docs(todo):` prefix, no bump.

3. **PR and merge.**
   ```bash
   gh pr create --base main --title "<conventional title>" --body "<what changed and why>"
   gh pr merge <N> --squash      # or --merge: pick one per repo and stick to it
   ```

4. **Deploy main.** Run the project's deploy skill (for production, the human runs the handoff). The health endpoint must report the target version and the merge commit.

5. **Tag + GitHub release - always together, on the commit that is live.**
   ```bash
   git fetch origin --tags
   git tag vX.Y.Z <live sha>
   git push origin vX.Y.Z
   gh release create vX.Y.Z --verify-tag --title "vX.Y.Z - <short description>" --notes "<what changed and why, user-facing>"
   ```
   Tag only what reached users. Never move or delete an existing tag. Skipped numbers (versions that never reached production) are normal and are never recycled.

6. **Delete the merged branch.** The release request is the confirmation for THIS branch only; any other branch needs explicit confirmation.
   ```bash
   git switch main && git fetch origin main && git merge --ff-only origin/main
   git branch -d <branch>
   git push origin --delete <branch>     # skip if the repo auto-deletes merged branches
   ```
   `-d`, never `-D`: it refuses an unmerged branch. If it refuses anywhere, stop and report.

7. **Record.** Update the project's learned facts if the release taught something (a trap, a missing step).

## Output

```
Released vX.Y.Z
PR #N merged (squash) -> main abc1234
Deployed: health reports vX.Y.Z / abc1234
Tag vX.Y.Z + GitHub release created on abc1234
Branch <branch> deleted (local, remote)
Work-log item closed: <item>
```

## What NOT to do

- No source-touching "Release vX" commit - the version lives in the feature commit, and a bare "Release" subject is not a conventional type.
- No tag before the version is live; no tag without a GitHub release, or the reverse.
- No force-push to main; no `git branch -D`.
- No production command run by the agent - production steps go through a human handoff.

## Project overrides (fill in)

- Merge method: `<--squash>`
- Deploy skill / procedure: `<deploy-vps | deploy-static | docs/runbooks/deploy.md>`
- Health URL: `<https://example.com/health>`
- Remote branches auto-deleted on merge: `<yes | no>`
