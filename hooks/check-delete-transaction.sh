#!/usr/bin/env bash
# PreToolUse hook (matcher Bash|PowerShell): destructive SQL typed into a database client.
#   DELETE FROM ... without BEGIN / START TRANSACTION in the same command -> deny
#   DROP TABLE|DATABASE|SCHEMA or TRUNCATE                                -> ask
#
# Why: a DELETE with a wrong or missing WHERE is unrecoverable without a restore. The required
# pattern is: BEGIN; DELETE ...; check the affected row count equals what you expected; COMMIT
# only if it does, otherwise ROLLBACK.
#
# Scope: only commands that invoke a SQL client (psql, mysql, sqlite3, bq, duckdb, ...), so a
# commit message such as "fix: delete from cart" is not blocked. It reads only the command
# text - keep the rule in AGENTS.md as well.
#
# Usage: bash check-delete-transaction.sh [--codex]
#   --codex: Codex does not support "ask" (the call would silently proceed), so DROP/TRUNCATE
#            are blocked with exit 2 instead.
DIALECT=claude
[ "${1:-}" = "--codex" ] && DIALECT=codex
PY=$(command -v python || command -v python3)
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; sys.stdout.buffer.write(((json.load(sys.stdin).get('tool_input') or {}).get('command') or '').encode('utf-8'))" 2>/dev/null) \
  || CMD=$INPUT

B='(^|[^[:alnum:]_])'
CLIENTS='(psql|pgcli|mysql|mariadb|mycli|sqlite3|litecli|duckdb|sqlcmd|bq|clickhouse|clickhouse-client|cockroach|turso)'
printf '%s' "$CMD" | grep -Eiq "(^|[^[:alnum:]_.-])$CLIENTS([^[:alnum:]_-]|\$)|prisma[[:space:]]+db[[:space:]]+execute|d1[[:space:]]+execute" || exit 0

emit() {  # emit <deny|ask> <reason>
  if [ "$1" = ask ] && [ "$DIALECT" = codex ]; then
    echo "$2 (Codex hooks cannot ask, so this is blocked: ask the human to run it.)" >&2
    exit 2
  fi
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' "$1" "$2"
  exit 0
}

if printf '%s' "$CMD" | grep -Eiq "${B}DELETE[[:space:]]+FROM[[:space:]]"; then
  printf '%s' "$CMD" | grep -Eiq "${B}(BEGIN|START[[:space:]]+TRANSACTION)([^[:alnum:]_]|\$)" \
    || emit deny "DELETE blocked: wrap it in a transaction - BEGIN; DELETE ...; check that the affected row count equals what you expect; COMMIT only if it does, otherwise ROLLBACK."
fi
if printf '%s' "$CMD" | grep -Eiq "${B}(DROP[[:space:]]+(TABLE|DATABASE|SCHEMA)|TRUNCATE)[[:space:]]"; then
  emit ask "Destructive DDL (DROP/TRUNCATE). Confirm the target database and environment, and that a backup exists."
fi
exit 0
