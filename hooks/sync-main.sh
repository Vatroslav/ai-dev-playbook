#!/usr/bin/env bash
# SessionStart hook: keep the main checkout on a current main without touching work in progress.
#   - on main, clean          -> fast-forward to origin/main
#   - on a branch that is merged (PR merged, or tip already in origin/main) and clean
#                             -> switch to main, then fast-forward
#   - dirty tree, unmerged branch, open PR, linked worktree -> touch nothing, report one line
# Never blocks session start: always exits 0. Its stdout lands in the agent's context.
#
# Why: project hooks and docs are read from the main checkout, so a stale branch there causes
# false blocks and stale reads. And not `git pull`: it reads the shared .git/FETCH_HEAD, which a
# parallel session's fetch can overwrite ("Cannot fast-forward to multiple branches").
set -u
MAIN="${SYNC_MAIN_BRANCH:-main}"
REMOTE="${SYNC_MAIN_REMOTE:-origin}"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
# A linked worktree belongs to one session's task - leave it alone.
[ "$(git rev-parse --git-dir 2>/dev/null)" != "$(git rev-parse --git-common-dir 2>/dev/null)" ] && exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
dirty=0; [ -n "$(git status --porcelain 2>/dev/null)" ] && dirty=1

if ! err=$(git fetch --quiet "$REMOTE" "$MAIN" 2>&1); then
  echo "main-sync: fetch failed ($err) - working offline on '$branch'."
  exit 0
fi

prefix=""
if [ "$branch" != "$MAIN" ]; then
  [ "$dirty" = 1 ] && { echo "main-sync: on '$branch' with uncommitted work - leaving it."; exit 0; }
  merged=0
  if command -v gh >/dev/null 2>&1; then
    state=$(gh pr view "$branch" --json state --jq .state 2>/dev/null || true)
    [ "$state" = MERGED ] && merged=1   # also catches squash merges (tip stays outside main)
  fi
  # Without gh: the tip is already in main (merge commit or fast-forward). A fresh branch cut from
  # main is "in main" too, so also require that commits were made on this branch locally
  # (its reflog has a "commit" entry) - otherwise it is new work that has not started yet.
  if [ "$merged" != 1 ] \
     && git merge-base --is-ancestor HEAD "$REMOTE/$MAIN" 2>/dev/null \
     && git log -g --format=%gs "refs/heads/$branch" 2>/dev/null | grep -q '^commit'; then
    merged=1
  fi
  if [ "$merged" != 1 ]; then
    echo "main-sync: on '$branch' (not merged into $MAIN) - leaving it."
    exit 0
  fi
  git switch --quiet "$MAIN" 2>/dev/null || { echo "main-sync: '$branch' is merged but switching to $MAIN failed - check manually."; exit 0; }
  prefix="'$branch' was merged, switched to $MAIN; "
elif [ "$dirty" = 1 ]; then
  echo "main-sync: $MAIN has uncommitted work - skipping update."
  exit 0
fi

if git merge-base --is-ancestor "$REMOTE/$MAIN" HEAD 2>/dev/null; then
  [ -n "$prefix" ] && echo "main-sync: ${prefix}already current."
elif out=$(git merge --ff-only --quiet "$REMOTE/$MAIN" 2>&1); then
  echo "main-sync: ${prefix}fast-forwarded to $REMOTE/$MAIN."
else
  echo "main-sync: ${prefix}fast-forward failed (local $MAIN has diverged?): $out"
fi
exit 0
