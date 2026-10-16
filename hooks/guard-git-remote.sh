#!/usr/bin/env bash
# PreToolUse hook (matcher Bash|PowerShell): pushes go only to remotes that already exist.
#
# Why: a broad Bash(*) allow lets `git push` go anywhere without a prompt. An injection can do
# `git remote add x <url>; git push x` or `git push <url>` and exfiltrate the repo, secrets in
# history included. This blocks:
#   - git remote add / set-url, and git config remote.<name>.url / pushurl (changing a destination)
#   - git push to an explicit URL (https://, ssh://, git://, file://, user@host:path)
# Pushing to an existing named remote such as `origin` stays free, so the normal
# commit-and-push workflow is untouched. The primary defense against leaked secrets is still the
# secret-scanning pre-commit hook; this is the second layer (control of the destination).
# If Python is missing, the raw hook JSON is scanned instead: more denials, never fewer.
PY=$(command -v python || command -v python3)
INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; sys.stdout.buffer.write(((json.load(sys.stdin).get('tool_input') or {}).get('command') or '').encode('utf-8'))" 2>/dev/null) \
  || COMMAND=$INPUT

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# POSIX ERE only (no \b, no grep -P): B = a word boundary before "git"
B='(^|[^[:alnum:]_-])'
GIT="${B}git([[:space:]]+-[cC][[:space:]]+[^[:space:]]+)*[[:space:]]+"

if printf '%s' "$COMMAND" | grep -Eq "${GIT}remote[[:space:]]+(add|set-url)([[:space:]]|$)"; then
  deny "git remote add/set-url is blocked (defense against redirecting pushes to an outside server). If the remote really has to change, a human does it."
fi
if printf '%s' "$COMMAND" | grep -Eiq "${GIT}config([[:space:]]+[^[:space:]]+)*[[:space:]]+remote\.[^[:space:]]+\.(push)?url"; then
  deny "Changing remote.<name>.url through git config is blocked (defense against redirecting pushes). If the remote really has to change, a human does it."
fi
if printf '%s' "$COMMAND" | grep -Eq "${GIT}push[[:space:]]+([^[:space:]]+[[:space:]]+)*(https?://|ssh://|git://|ftp://|file://|[[:alnum:]._-]+@[[:alnum:]._-]+:)"; then
  deny "git push to an explicit URL is blocked (exfiltration defense). Push to an existing named remote such as origin."
fi
exit 0
