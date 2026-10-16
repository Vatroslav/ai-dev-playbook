#!/usr/bin/env bash
# PreToolUse hook (matcher Write|Edit): ask for confirmation when an EXISTING file that is not
# under git is about to be overwritten. The criterion is irreversibility, not location:
# inside a repo git is the undo, outside it there is none.
#
# Passes silently:
#   - a file that does not exist yet (a new file destroys nothing)
#   - anything inside a git work tree (any repo)
#   - temp / scratch locations
#   - the agent's auto-memory folder (~/.claude/projects/*/memory/)
# Scope: the Write/Edit tools only. Deletes are covered by guard-rm.sh for every location.
# A blanket Write(*)/Edit(*) allow does NOT switch this off - a hook "ask" still prompts.
# Claude Code only: Codex edits files through apply_patch, whose input has no file_path.
INPUT=$(cat)
PY=$(command -v python || command -v python3)
FP=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; sys.stdout.buffer.write(((json.load(sys.stdin).get('tool_input') or {}).get('file_path') or '').encode('utf-8'))" 2>/dev/null) || {
  # Python missing: pull file_path out of the raw JSON (exact key, value up to the next quote)
  FP=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1 | sed 's#\\\\#\\#g')
}

[ -z "$FP" ] && exit 0

# Windows backslashes -> forward slashes (Git Bash understands C:/... in file tests)
FP="${FP//\\//}"
LOWER=$(printf '%s' "$FP" | tr 'A-Z' 'a-z')

# Locations where overwriting never needs confirmation
case "$LOWER" in
  */appdata/local/temp/*)          exit 0 ;;  # Windows temp / scratchpad
  /tmp/*|/var/folders/*|/private/var/folders/*) exit 0 ;;  # Linux / macOS temp
  */.claude/projects/*/memory/*)   exit 0 ;;  # auto-memory protocol
esac

# New file - nothing to lose
[ -f "$FP" ] || exit 0

# Is there a git repo above it? Git is the undo - let it through.
DIR=$(dirname "$FP")
if git -C "$DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# Existing file, not versioned - the only case that asks
REASON="Overwrites an existing file that is not in a git repo (no undo): $FP"
"$PY" -c "import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'ask','permissionDecisionReason':sys.argv[1]}}))" "$REASON" 2>/dev/null \
  || echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Overwrites an existing file that is not in a git repo (no undo). Guard is in fallback mode (Python not working)."}}'
exit 0
