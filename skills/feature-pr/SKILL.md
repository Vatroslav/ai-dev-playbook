---
name: feature-pr
description: Ship a finished, verified code change to main - branch, intent-based version bump, a commit that passes the version-guard hook (separate staging call, literal -m, explicit pathspec), PR, copy gate, auto-merge on green CI, then confirm the merge commit is live on staging via the health endpoint. Use when a code task is done and verified ("ship it", "open the PR", "merge this", "we're done, push it"). NOT for production deploys (a human starts those) and NOT for tagging a release in repos without auto-merge (use release).
---

# Feature PR - the shipping cycle

Policy lives in `docs/agent/git-workflow.md`; the version model in `docs/agent/versioning.md`. This skill is the execution order plus the traps that commonly stop a commit.

Why: with several agent sessions and teammates sharing one repo, most shipping failures are mechanical - a commit that sweeps up someone else's staged files, a bump the hook can't see, a PR that merged but never reached staging. The order below prevents each of them.

## Preflight

- Not a git repo, or no remote -> `SKIP: no git remote`.
- `gh auth status` fails -> `SKIP: GitHub CLI not authenticated - a human runs gh auth login`.
- The change is not verified yet (no test/build evidence in this session) -> run evidence-first first.
- `git status --porcelain` shows files you did not change -> STOP and report. Never mix them in.

## Steps

1. **Branch.** On `main`: `git fetch origin && git switch -c <type>/<short-slug> origin/main`. In a worktree session, run every git command as `git -C "<worktree>" ...` and never `cd` into the main checkout (it has `main` checked out with other people's work; your commit would land there).

2. **Version bump by intent**, in the SAME commit as the change: `feat` -> minor, `fix`/`perf` -> patch, breaking (`!:` / `BREAKING CHANGE`) -> major; `docs`, `chore`, `refactor`, `style`, `test`, `ci`, `build` -> none. Edit the version file by hand. On a feature branch that will receive several sub-PRs, bump once at merge time instead (see `docs/agent/git-workflow.md`).

3. **Local checks.** Tests for touched modules; typecheck including test files; lint only your own files (CI is the authority on the rest). New data surface -> run data-surface-gates. UI ported from a design handoff -> run design-fidelity. Changed user-visible strings -> follow copy-voice.

4. **Stage in a SEPARATE tool call, then commit.**
   - `git add <files by name> <version file>` as its own call. Never `-A` or `.`. Why: a PreToolUse version hook inspects the commit command before it runs and cannot see a bump staged in the same `&&` chain.
   - Commit with a literal `-m` (multi-line inside the quotes is fine), conventional prefix, `-m` before `--`, explicit pathspec (parallel sessions share the git index):
     ```
     git commit -m "fix(cart): keep discount when quantity changes

     The discount was recomputed from the unit price only.
     Adds a regression test." -- src/cart/total.ts src/cart/total.test.ts package.json
     ```
     Add only the trailer your team or harness requires. Avoid backticks inside a double-quoted `-m` in bash (command substitution silently eats the text).

5. **Push and open the PR.**
   ```
   git push -u origin <branch>
   gh pr create --base main --title "<same conventional title>" --body "<what and why; Gates / Deviations sections when applicable>"
   ```
   The PR title becomes the squash commit message, and CI reads the type from it.

6. **Copy gate.** If the diff touches message catalogs, release notes or any user-visible string: print ALL changed copy in chat, every locale, and wait for an explicit "ok". Never "arm it and check on staging". Internal admin-tool copy: list it in the PR body and continue.

7. **Arm auto-merge and report.**
   ```
   gh pr merge <PR> --auto --squash
   ```
   Post: "PR #N - auto-merge armed" (the human can disarm with `gh pr merge <PR> --disable-auto`). Before pushing any follow-up commit later, check the PR is still open: `gh pr list --head <branch> --state open`. Commits pushed to a merged branch are stranded.

8. **After merge - verify the staging deploy (mandatory).**
   1. `gh run list --workflow=<deploy workflow> --limit 3` -> a successful run for the merge commit.
   2. `curl -s <staging-url><health-path>` -> compare its `commit`/`sha` with `git rev-parse --short <merge sha>`. Read the health endpoint, never the UI footer.
   3. Report: "Deployed to staging: vX.Y.Z (sha abc1234, confirmed on <health-path>)".
   4. Return the main checkout to fresh main, if it is clean and its branch has no open PR (otherwise leave it and report): `git -C <main-checkout> switch main && git -C <main-checkout> fetch origin main && git -C <main-checkout> merge --ff-only origin/main`. Skip this in a worktree session - leave your worktree alone. Use fetch + `merge --ff-only`, not `git pull`: concurrent fetches from other sessions overwrite the shared `FETCH_HEAD`. Why bother: hooks and fresh sessions run from the main checkout, and a stale branch there causes false hook blocks and stale reads.

9. **Production is not part of this cycle.** Don't propose or mention a prod deploy; a human initiates it.

## Quick fixes

| Symptom | Cause | Fix |
|---|---|---|
| Hook: "version not bumped" but it is | `git add` in the same chain as the commit | stage separately, repeat only the commit |
| Hook: "intent not declared" though the message starts with `feat:` | heredoc or `$(...)` message the hook can't parse | literal `-m` |
| Commit picked up others' files / landed on main | shared index / `cd` into the main checkout | explicit pathspec + `git -C`; recover with `git cherry-pick`, never `reset --hard` |
| CI fails on the version step | suffix, no bump, version decreased, or PR title lacks a type | fix on the branch |
| PR stuck on "Expected" check | required check skipped by a path filter | see `docs/agent/ci-cd-and-deploy.md` |

## Headless mode

Unattended runs stop after step 7 if the copy gate applies (no one can say "ok"): open the PR, do not arm, and report "copy gate pending". Otherwise run through step 8 and report the staging confirmation line or the exact failure.

## What NOT to do

- No `git add -A`, no commit without a pathspec, no `reset --hard`, no force-push.
- No arming auto-merge on a copy PR before "ok", or on a feature-branch PR before the human says "merge".
- No changing repository settings (auto-merge, branch protection, rulesets).
- No "fixing" lint in files you didn't touch.

## Project overrides (fill in)

- Version file: `<package.json | pyproject.toml | VERSION>`
- Merge method: `<--squash>`
- Deploy workflow: `<deploy-staging.yml>`
- Staging URL and health path: `<https://staging.example.com>` `</api/health>` (returns `version` and `commit`)
- Message catalogs (copy gate trigger): `<messages/*.json>`
