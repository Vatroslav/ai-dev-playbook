#!/usr/bin/env bash
# PreToolUse hook (matcher Bash|PowerShell): deny shell commands that read secret files.
#
# Why: `deny: Read(**/secrets/**)` and `Read(**/.env)` only cover the Read tool. With a broad
# Bash(*) allow, a prompt injection can read a token through the shell (cat, type, Get-Content,
# python -c "open('secrets/...')") and exfiltrate it. This closes the easy paths:
#   1. any command that mentions a secrets/ path
#   2. a reader command (cat, grep, head, Get-Content, curl -d @...) on a real env file
#      (.env, .env.local, .env.production, ...). Templates (.env.example, .env.sample) pass,
#      and so do writes such as `cp .env.example .env`.
# Pattern guards parse command text; they are a speed bump, not a sandbox. Use a container or
# VM for a real boundary. Intended pattern: a script that needs a token opens the file itself
# and never prints it.
# If Python is missing, the raw hook JSON is scanned instead: more denials, never fewer.
PY=$(command -v python || command -v python3)
INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; sys.stdout.buffer.write(((json.load(sys.stdin).get('tool_input') or {}).get('command') or '').encode('utf-8'))" 2>/dev/null) \
  || COMMAND=$INPUT

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# 1. 'secrets/' or 'secrets\' as a path (not the bare word in a commit message)
if printf '%s' "$COMMAND" | grep -Eq 'secrets[/\\]'; then
  deny "Command touches a secrets/ path. Reading or sending secret file contents through the shell is blocked (prompt-injection exfiltration defense). If a secret is really needed, a human handles it outside the agent, or a script opens the file internally without printing it."
fi

# 2. reader + real env file in the same command segment (POSIX ERE, case-insensitive for cmdlets)
# `cut -d= -f1 .env` (names only) is deliberately not a reader.
READERS='(cat|tac|type|less|more|head|tail|grep|egrep|fgrep|rg|ag|sed|awk|sort|strings|xxd|od|hexdump|base64|nl|bat|get-content|gc|select-string|sls|findstr|curl|wget|scp|nc)'
ENVFILE='\.env(rc|\.(local|development|dev|staging|stage|production|prod|test)(\.local)?)?([^[:alnum:]_.-]|$)'
if printf '%s' "$COMMAND" | grep -Eiq "(^|[^[:alnum:]_.-])$READERS[[:space:]][^;&|]*$ENVFILE"; then
  deny "Command reads a real env file (.env, .env.local, .env.production...). Its values are secrets and would land in the transcript. Read .env.example for the variable names, or ask the human to export the variable."
fi
exit 0
