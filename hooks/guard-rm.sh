#!/usr/bin/env bash
# PreToolUse hook (matcher Bash|PowerShell): force an "ask" prompt for a command that really
# deletes something that has no undo. Never blocks in Claude Code, only asks.
#
# Why: a broad Bash(*) allow otherwise lets deletes run without confirmation. The criterion is
# irreversibility, not location:
#   - temp / scratch targets pass silently (tmp_x.py, /tmp/..., $TEMP\...)
#   - files tracked by git with no uncommitted changes pass silently (git restores them)
#   - everything else asks, with the exact trigger in the prompt
# A guard that prompts for routine work gets switched off, so the silent cases matter as much
# as the prompting ones.
#
# Usage:
#   bash guard-rm.sh           Claude Code: prints an "ask" decision
#   bash guard-rm.sh --codex   Codex: "ask" is parsed but not supported there (the call would
#                              silently proceed), so the call is BLOCKED with exit 2 instead
#
# The decision is made by guard-rm-reason.py next to this file. If Python is missing or the
# script crashes, a blunt grep over the whole command decides and always asks.

DIALECT=claude
[ "${1:-}" = "--codex" ] && DIALECT=codex

# Interpreter: prefer `python`, then `python3`. On Windows `python3` is often the Microsoft
# Store stub; on macOS only `python3` exists.
PY=$(command -v python || command -v python3)
INPUT=$(cat)

# Parse the hook JSON with a real JSON parser - never greedy sed (it also captures the
# `description` field) and never jq (often not installed). First line = cwd, rest = command.
# Raw bytes on stdout: a text-mode print() on Windows turns \n into \r\n.
if PARSED=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "
import json, sys
d = json.load(sys.stdin)
cwd = (d.get('cwd') or '').replace('\n', ' ')
cmd = (d.get('tool_input') or {}).get('command') or ''
sys.stdout.buffer.write((cwd + '\n' + cmd).encode('utf-8'))" 2>/dev/null); then
  PARSE_OK=1
  HOOK_CWD=${PARSED%%$'\n'*}
  COMMAND=${PARSED#*$'\n'}
  # Git Bash: a POSIX-style cwd (/c/..., /tmp/...) means nothing to a native Windows Python
  case "$HOOK_CWD" in
    /*) command -v cygpath >/dev/null 2>&1 && HOOK_CWD=$(cygpath -m "$HOOK_CWD") ;;
  esac
else
  PARSE_OK=0
  # Parser unavailable: scan the raw JSON. More prompts, never fewer - and the extra prompts
  # make the broken interpreter visible.
  HOOK_CWD=''
  COMMAND=$INPUT
fi

# Normalise escaped exclamation marks (\! -> !) so exact-match allowlist entries work
COMMAND="${COMMAND//\\!/!}"

# Optional exact-match allowlist for routine deletes used by your own skills/scripts
case "$COMMAND" in
  "rm -f /tmp/example-skill-flag") exit 0 ;;
esac

block_or_ask() {
  if [ "$DIALECT" = codex ]; then
    echo "$1 Codex hooks cannot ask for confirmation, so this call is blocked: ask the human to run it." >&2
    exit 2
  fi
  "$PY" -c "import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'ask','permissionDecisionReason':sys.argv[1]}}))" "$1" 2>/dev/null \
    || echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Command contains a delete - requires confirmation (guard is in fallback mode: Python not working)"}}'
  exit 0
}

REASON_PY="${GUARD_RM_REASON_PY:-$(dirname "$0")/guard-rm-reason.py}"
if [ "$PARSE_OK" = 1 ] \
   && REASON=$(printf '%s' "$COMMAND" | GUARD_RM_CWD="$HOOK_CWD" PYTHONIOENCODING=utf-8 "$PY" "$REASON_PY" --plain 2>/dev/null); then
  [ -n "$REASON" ] && block_or_ask "$REASON"
  exit 0
fi

# Fallback (Python missing, hook JSON unparseable, or the reason script crashed):
# grep -w over the whole text, always asks.
# Remove this hook's own file names - they contain "rm" as a separate word.
COMMAND="${COMMAND//guard-rm-reason.py/}"
COMMAND="${COMMAND//guard-rm.sh/}"
if echo "$COMMAND" | grep -qwE 'rm|rmdir' \
   || echo "$COMMAND" | grep -qiwE 'Remove-Item|del|erase|rd|ri' \
   || echo "$COMMAND" | grep -qiE '(::|\.)[[:space:]]*Delete(File|Directory)?[[:space:]]*\('; then
  block_or_ask "Command contains a delete (rm/rmdir, PowerShell Remove-Item/del/rd/ri/erase or .NET Delete) - requires confirmation. Guard is in fallback mode (Python not working), so temp and clean tracked files are not recognised."
fi

exit 0
