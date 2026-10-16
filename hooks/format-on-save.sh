#!/usr/bin/env bash
# PostToolUse hook (matcher Write|Edit): format the one file the agent just touched.
#
# - Only files INSIDE this repo: the hook fires on every Write/Edit of the session, and this
#   repo's formatter config has no say over the style of files outside it.
# - JS/TS tools run from the NEAREST directory with a package.json (monorepos: each package has
#   its own node_modules and config) with `npx --no-install`, so nothing is downloaded on the fly.
# - Markdown is left alone: docs are prose, not generated output (add it below if you want).
# - Never blocks and never fails the call: formatter errors are swallowed on purpose.
# Keep only the branches for stacks this repo uses. Claude Code only (Codex edits through
# apply_patch, whose input has no file_path).
export PYTHONIOENCODING=utf-8
PY=''
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then PY=$c; break; fi
done
[ -z "$PY" ] && exit 0

input=$(cat)
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$root" ] && exit 0

# Print the path only if it resolves inside the repo root (symlinks and case folded)
file_path=$(printf '%s' "$input" | ROOT="$root" "$PY" -c "
import json, os, sys
p = (json.load(sys.stdin).get('tool_input') or {}).get('file_path') or ''
n = lambda x: os.path.normcase(os.path.realpath(x))
inside = p and n(p).startswith(n(os.environ['ROOT']).rstrip(os.sep) + os.sep)
sys.stdout.write(p.replace(os.sep, '/') if inside else '')" 2>/dev/null)
[ -n "$file_path" ] && [ -f "$file_path" ] || exit 0

nearest_pkg() {
  local d
  d=$(dirname "$1")
  while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do
    [ -f "$d/package.json" ] && { echo "$d"; return; }
    case "$d" in [A-Za-z]:/) return ;; esac
    d=$(dirname "$d")
  done
}

case "$file_path" in
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.vue|*.svelte)
    pkg=$(nearest_pkg "$file_path"); [ -z "$pkg" ] && exit 0
    ( cd "$pkg" && npx --no-install prettier --write --log-level silent "$file_path"
                   npx --no-install eslint --fix "$file_path" ) >/dev/null 2>&1
    ;;
  *.json|*.css|*.scss|*.html|*.yaml|*.yml)
    pkg=$(nearest_pkg "$file_path"); [ -z "$pkg" ] && exit 0
    ( cd "$pkg" && npx --no-install prettier --write --log-level silent "$file_path" ) >/dev/null 2>&1
    ;;
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format --quiet "$file_path" >/dev/null 2>&1
      ruff check --fix --quiet "$file_path" >/dev/null 2>&1
    fi
    ;;
  *.kt|*.kts)
    command -v ktlint >/dev/null 2>&1 && ktlint --format "$file_path" >/dev/null 2>&1
    ;;
esac
exit 0
