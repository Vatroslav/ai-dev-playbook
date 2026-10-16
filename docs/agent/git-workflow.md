# Git workflow

Purpose: how agents and teammates branch, commit, sync, open PRs and merge without trampling each other's work.
Read when: before committing, opening or merging a PR, recovering from a git mistake, or running several agent sessions in parallel.

Several agent sessions and several teammates share one repository, often one machine and one `.git` folder. Most rules below exist because of that: the git index, `HEAD`, `FETCH_HEAD` and the main checkout are shared state.

## Before you start a task

- **Fetch first, then check whether the work is already done.** Run `git fetch origin`, then look at `origin/main` and at open and recently closed PRs:
  ```bash
  git fetch origin
  git log origin/main --oneline -20
  gh pr list --state all --limit 30 --search "<keyword>"
  ```
  Why: a parallel session or a teammate may already have shipped it, and without the check the same work gets built twice.
- **If `git status` shows changes you didn't make, stop and report.** Never fold them into your commit, never stash or discard them. Why: they belong to another session or person, and they are the only copy.
- **One branch per task, created from a freshly fetched `origin/main`, named `<type>/<short-slug>`.**
  ```bash
  git fetch origin
  git switch -c feat/csv-export origin/main
  ```
  Types match commit types: `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`. Never commit directly to main. Why: a stale base means conflicts and re-testing later; a direct commit to main skips CI.
- **Compute anything that must be globally unique from `origin/main` plus all open PR branches, never from your local copy.** That covers task IDs and the next version number:
  ```bash
  for b in $(gh pr list --state open --json headRefName -q '.[].headRefName'); do
    git show "origin/$b:package.json" 2>/dev/null | grep '"version"'
  done
  git show origin/main:package.json | grep '"version"'
  ```
  Why: two parallel branches that compute the "next" ID or version from the same stale base get the same value. Guards check the format of a version, not its uniqueness.

## Parallel sessions: one worktree each

- **Give every parallel agent session its own git worktree, and every teammate's agent its own worktree or clone.**
  ```bash
  git fetch origin
  git worktree add ../app-csv-export -b feat/csv-export origin/main
  ```
  Why: sessions in the same working copy share `HEAD` and the index. One session switching branch moves the other session's commits onto the wrong branch.
- **Inside a worktree session, address git explicitly with `git -C <worktree>` and use absolute paths; never `cd` into the main checkout.** Why: the main checkout has `main` (or someone else's branch) checked out, so a commit made there lands on the wrong branch with someone else's files. Tools and subagents often return main-checkout paths, and shell `cwd` carries over between calls.
- **Run `git -C <worktree> branch --show-current` right before every commit.** Why: it is the cheapest check that you are where you think you are.
- **Keep the main checkout clean and on `main`.** Agent hooks and session-start scripts often run from the main checkout; a stale feature branch there causes false hook blocks and stale reads.
- **Exclude worktree folders from test discovery and linting** (for example `.claude/worktrees/**`). See [testing](testing.md#conventions). Why: the local run otherwise picks up duplicate copies of every test.
- **Never touch another session's worktree or another repo's working tree.** Read other code with `git -C <repo> show origin/main:<path>`.

## Staging and committing

- **Stage files by name; never `git add -A`, `git add --all` or `git add .`.** Why: they sweep in scratch files, a stray `.env`, or another session's work.
- **Commit with an explicit pathspec.**
  ```bash
  git add src/export/csv.ts src/export/csv.test.ts package.json
  git commit -m "feat(export): add CSV export of the report table" -- src/export/csv.ts src/export/csv.test.ts package.json
  ```
  Why: the index is shared by every session and subagent in one checkout. A commit without a pathspec pulls another session's staged files into the wrong PR.
- **Use a conventional commit type on every commit that touches source** (`feat`, `fix`, `perf`, `docs`, `refactor`, `style`, `test`, `chore`, `ci`, `build`, `revert`). The type drives the version bump; see [versioning](versioning.md).
- **Pass the message so that hooks can read it: `-m "..."` (multi-line inside the quotes is fine) or `-F <file>`.** Avoid `-F -`, editor-based messages and `$(...)` command substitution. Stage in a separate command from the commit when a hook inspects the staged diff. Why: a PreToolUse hook sees the command text before it runs; it cannot read stdin and cannot see a file staged later in the same `&&` chain, which produces false blocks.
- **In bash, never put backticks inside a double-quoted `-m "..."`.** Use single quotes or plain words. Why: backticks run as command substitution and silently delete words from the message.
- **Get the commit message right the first time.** Why: pushed history can only be fixed with a force push, which is forbidden, so a wrong message stays forever.
- **Docs change in the same commit as the code they describe** (README, ADR, feature doc). A PR without updated docs does not merge. Why: the next agent session trusts the README; a README that lies costs a whole session.
- **Cleanup is part of the feature:** delete dead code, unused imports, commented-out blocks and `_old` / `_backup` / `_v2` files in the same change. Why: git keeps history; the working tree doesn't need to.
- **Comments explain why, never what.** Comment especially where a reader might think "this looks wrong, let me fix it". Why: the next agent will otherwise "fix" an intentional decision.
- **Never delete or "simplify" code marked as a live migration.** Marker: `// MIGRATION-IN-PROGRESS: kept until cutover on YYYY-MM-DD, do not delete`. Cutover is one explicit commit that removes the marker and the old path together; refactor only the new path. If the date has passed and the state is unclear, ask. Why: during a migration, old and new paths run in parallel, and agents delete unused-looking code that production still needs.
- **Never run a formatter over a whole existing file; format only what you wrote.** Check `git diff --stat` against what you meant to change before committing. Why: a whole-file reformat buries the real change in noise and breaks blame. Format-on-save hooks must touch only the edited file.
- **Don't fix pre-existing lint findings in files you didn't touch.** CI is the authority. Why: it keeps the diff reviewable and scoped.
- **Don't commit hypotheses into permanent docs while you are still investigating.** Commit once, when the finding has settled. When you delete content, decide where it moves first. Why: a chain of contradictory commits is worse than no commit, and deleted-but-not-moved knowledge is lost.
- **Never commit secrets or weaken `.gitignore`.** The secret-scanning pre-commit hook must pass; never use `--no-verify` to get past it. See [security](security.md).

## Syncing and pushing

- **Sync with `git fetch origin main && git merge --ff-only origin/main`, not `git pull`.** Why: `git pull` reads the shared `.git/FETCH_HEAD`. A concurrent fetch from another session overwrites it, and the pull fails with "Cannot fast-forward to multiple branches", or worse, merges the wrong thing.
- **Before pushing, fetch and read the incoming commits that touch your area.**
  ```bash
  git fetch origin
  git log --oneline HEAD..origin/main -- src/export/
  ```
  If someone else's fix is better, rebuild your remaining contribution on top of it. Never force-push, never rebase shared branches blindly.
- **When main moved, merge `origin/main` into your branch and resolve conflicts on the branch, then confirm nothing was lost:**
  ```bash
  git merge origin/main
  git diff origin/main...HEAD --stat
  ```
  Every intended change must still appear. Why: a conflict resolution can silently drop code that had been tested.
- **Before pushing a follow-up commit, check that the branch's PR is still open:** `gh pr list --head <branch> --state open`. Why: commits pushed to an already merged branch are stranded, and with delete-on-merge they recreate the branch with no PR.

## Recovering from mistakes

- **Never `git reset --hard`, never `git checkout -- .` or `git clean -fd` on a shared checkout.** Recover with `cherry-pick`. Why: reset destroys uncommitted work that may belong to a parallel session.
  ```bash
  # A commit landed on the wrong branch (e.g. local main). Note its SHA, then:
  git switch -c fix/the-real-branch origin/main
  git cherry-pick <sha>
  # Only after confirming the commit is safe on the new branch, and with main NOT checked out anywhere:
  git branch -f main origin/main
  ```
- **If the main checkout is held by another worktree or session, branch from `origin/main` instead of taking it over.**
- **Fix forward; don't revert as a safety net.** Repair living code, config and docs with a new commit. Use history to look things up, not as a restore button. Why: a revert weeks later stomps on newer edits, and promising "we can always revert" gives false safety.
- **When two guards collide, change your route; never bypass a guard.** No `--no-verify`, no `--admin` merge, no disabling a hook to get through. If a hook blocks you and you believe it is wrong, stop and report it to a human. Why: a bypassed guard protects nobody, and a blocked action routed through another session or tool is permission laundering.

## Pull requests

- **The PR title becomes the squash commit message, so it carries the conventional type.** CI reads the type from the title to decide whether a version bump is required (see [versioning](versioning.md)).
- **Fill in the [PR template](../../ci/pull_request_template.md).** It holds the merge checklist: no stubs, tests (including a failing-before test for bug fixes), lint and types, version, docs, cleanup, no secrets, user-visible copy, deviations from the design, and steps a human must run. A PR with an empty template is not ready.
- **Keep PRs small and independent.** Why: small PRs make auto-merge safe, keep conflicts rare and make review possible.

### Auto-merge on green CI

The team's policy: when a task is done, the agent ships it through CI without waiting in a human merge queue. A human in the merge queue is only a serialization point; structural mechanisms do that job better.

- **How a task ends:**
  1. Branch, commit, push, open the PR to `main`.
  2. Copy gate (see below), if the diff touches user-visible text.
  3. Check the PR head is your commit: `gh pr view <N> --json headRefOid -q .headRefOid` equals `git rev-parse HEAD`.
  4. Arm: `gh pr merge <N> --auto --squash`.
  5. Report in chat: "PR #N, auto-merge armed". A human can disarm with `gh pr merge <N> --disable-auto`.
  6. Return the main checkout to `main` and fast-forward right away, without waiting for the merge (sessions often end first). A worktree session leaves its own worktree alone.
- **Why this is safe** (these must all be true; if one is missing, don't arm auto-merge):
  - a required status check (`check`) gates every merge;
  - the default-branch ruleset blocks force pushes and deletion, with no bypass, so two near-simultaneous merges can't corrupt main;
  - merging to main deploys staging only; production is a manual human action;
  - non-strict mode (branches need not be up to date) avoids rebase treadmills.
  Accepted residual risk: a semantic conflict between two green PRs. PRs are small, and the impact lands on staging, where the post-deploy smoke test catches it.
- **What still waits for a human:**
  1. **User-visible copy.** Print every changed user-facing string, in every locale, in chat, and arm only after the product owner says "ok". Never "arm it and look on staging". Internal admin-tool copy is exempt: list it in the PR description and arm.
  2. **Feature branches** (below): never into main without an explicit "merge".
  3. **Anything in production.** The agent never deploys to production and doesn't propose it during the feature cycle; a human initiates it.
  4. **Repository settings** (auto-merge, rulesets, branch deletion): the admin's decision, never the agent's.
  5. **Dependabot PRs:** a human reads and merges them.
- **Allowlist only the safe merge form for agents.** Allow `gh pr merge <N> --auto --squash`; route `--admin`, `--delete-branch` / `-d`, `--repo` / `-R` to "ask". Why: `--admin` bypasses the required check, and the other flags act outside the PR you meant.

### Auto-merge hygiene

- **After arming, push nothing more to that branch.** If you need a change, disarm first, or open a new PR. Why: squash-merge plus delete-on-merge silently drops late commits and recreates the branch with no PR.
- **Watch the PR itself, not the downstream deploy, and make watchers exit on every terminal state:** merged, check failed, conflict, closed. Why: a loop that only waits for "merged" never ends when a check fails.
- **Tie every wait to your own event, the merge commit SHA, never to "the latest run".** Why: other sessions' runs overtake yours, and you end up verifying someone else's deploy.
  ```bash
  SHA=$(gh pr view <N> --json mergeCommit -q .mergeCommit.oid)
  gh run list --workflow deploy-staging.yml --commit "$SHA" --json status,conclusion
  ```

### Feature branches: develop in parallel, merge serially

Use a feature branch when the task is a design handoff, covers a whole screen, or clearly needs several PRs. If unclear, ask one question at the start ("Should this go on a feature branch?"), never mid-work.

1. Create `feature/<slug>` from fresh `origin/main` and open a **draft** PR to main (`gh pr create --draft`). Never arm it.
2. Sub-PRs target the feature branch and may auto-merge into it.
3. Merge `origin/main` into the feature branch regularly.
4. Bump the version once, at merge time, not per sub-PR (parallel bumps from the same base conflict).
5. On the human's "merge": update from main, resolve conflicts, bump, show the copy, `gh pr ready`, arm.
6. **Only one feature branch goes into main at a time.** Before `gh pr ready`, check whether another PR is already armed:
   ```bash
   gh pr list --base main --state open --json number,title,autoMergeRequest \
     --jq '.[] | select(.autoMergeRequest != null) | "\(.number) \(.title)"'
   ```
   Non-empty output: wait for that PR to land, then update, bump and arm.

Why: parallel sessions that arm auto-merge at the same time collide on the version number, the message catalogs and the task tracker. When many PRs keep colliding on the version file, let one session own the merge queue and merge one PR at a time.

### Squash-merge traps

- **Avoid stacked PRs when the repo squash-merges.** After the base PR is squashed, the stacked branch still carries the original commits and goes "dirty". If it happens, merge `main` into it and resolve; don't rebase and force-push.
- **`git branch --merged` cannot see squash-merged branches.** Use either of:
  ```bash
  gh pr list --state merged --head <branch>
  git merge-base --is-ancestor <branch> origin/main
  ```

## After the merge

- **Return the main checkout to `main` and fast-forward:** `git -C <main-checkout> switch main && git -C <main-checkout> merge --ff-only origin/main` (after a fetch). At session start, do the same check: on main and behind, fast-forward; on a merged, clean branch, switch to main; dirty or with an open PR, leave it alone and report.
- **Verify the staging deploy of your merge commit,** not "the latest run", and confirm the live SHA on the health endpoint. Procedure in [CI/CD and deploy](ci-cd-and-deploy.md#after-every-deploy).

## Deleting branches and worktrees

- **Remote branches:** the repository deletes them on merge (`delete_branch_on_merge`). That is not an agent action, and a deleted branch can be restored from the PR page.
- **Local branches are deleted only with explicit confirmation, or by a cleanup task that applies all of these criteria:**
  - never `main`, never a branch with an open PR, never a branch checked out in a live worktree;
  - delete only if the branch has a merged PR or its tip is already in `origin/main` (checked as in "Squash-merge traps");
  - list, but never delete, branches that are unmerged or whose PR was closed without merging; that decision is a human's.
- **Use `git branch -d` by default; it refuses unmerged branches.** A squash-merged branch looks unmerged to git, so `-d` refuses it: verify the merged PR first, and only then use `-D`. If `-d` refuses for any other reason, stop and report.
- **Remove a worktree only if all four hold:** its `git status --porcelain` is empty, its branch is merged, nothing in it changed for several days (a stand-in for "no live session"), and it is not the main checkout. Then `git worktree remove <path>` and `git worktree prune`. On Windows, removal can fail with "Filename too long" (deep `node_modules`) yet still unregister the worktree; delete the folder separately.

## Repository setup checklist (for the admin)

- Ruleset on main: required check `check`, block force pushes, restrict deletions, no bypass, branches need not be up to date.
- Allow auto-merge and squash merging; delete head branches automatically.
- `.gitattributes` contains `*.sh text eol=lf`, and shell scripts are executable (`git update-index --chmod=+x script.sh`). Why: CRLF line endings make bash fail with "bad interpreter".
- Agent hooks are registered in the committed `.claude/settings.json` (or your agent's equivalent), so every teammate and worktree gets them. A global `core.hooksPath` (for example a secret scanner) disables repo-local `.git/hooks`, so per-repo enforcement belongs in agent hooks and CI.
- Repos are private by default; make one public only for a stated reason. Everything in a public repo, including comments and commit messages, is written in English.
