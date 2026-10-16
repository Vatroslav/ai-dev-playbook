#!/usr/bin/env bash
# PreToolUse hook (matcher Bash|PowerShell): explicit staging and explicit commits.
#
# 1. Deny `git add -A`, `git add --all`, `git add .` - they sweep in files that do not belong
#    in the commit (scratch files, a stray .env, another session's work). Add files by name.
# 2. Deny `git commit` without paths. A path-less commit commits the WHOLE index, and the index
#    is shared by every session and subagent working in the same checkout - one session's
#    commit silently takes files another session staged. Allowed: `git commit ... -- path1
#    path2`, `--only`, and `--no-edit` (concluding a merge). Every commit in the command needs
#    its own paths. (Two sessions editing the SAME file need separate worktrees - no hook fixes that.)
PY=$(command -v python || command -v python3)
INPUT=$(cat)
# JSON parser, not greedy sed: sed can also match the `description` field, so a pattern in the
# description would deny a harmless command.
# If Python is missing, the raw hook JSON is scanned instead: more denials, never fewer.
COMMAND=$(printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; sys.stdout.buffer.write(((json.load(sys.stdin).get('tool_input') or {}).get('command') or '').encode('utf-8'))" 2>/dev/null) \
  || COMMAND=$INPUT

# POSIX ERE only (no \b, no grep -P - both silently fail on some platforms): B = word boundary
B='(^|[^[:alnum:]_-])'

# git add -A / --all / . (bounded by space, end of string, ; & | or a closing quote)
if printf '%s' "$COMMAND" | grep -Eq "${B}git[[:space:]]+add[[:space:]]+(-A|--all|\\.)([[:space:]]|\$|;|&|\\||\")"; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Do not use git add -A / --all / . - add files explicitly by name (git add path1 path2). Reason: it can sweep in files that do not belong in this commit."}}'
  exit 0
fi

# Commit check. Python makes the decision and runs only when the command contains `git commit`.
# It reads the command twice:
# - MASKED: contents of quotes, PowerShell here-strings (@'...'@) and heredoc bodies replaced
#   by `_`, comments removed. Commits and their paths are looked up here - otherwise a `;`, `&`
#   or `|` inside the message (-m "a; b") cuts the pattern and a commit WITH paths gets denied,
#   and ` -- x` inside a message would falsely pass.
# - SHELL: quotes intact, only comments and data heredoc bodies removed. If there is no
#   `git commit` here, the command merely mentions one (cat > notes.md <<'EOF', python - <<'EOF',
#   gh pr create --body "$(cat <<'EOF' ...)") and passes. If there is one here but not in the
#   masked text (bash -c "git commit ...", echo "git commit"), deny - fail closed.
# A heredoc body is data when a non-shell program consumes it (DATA), the delimiter is quoted or
# the body has no $( or backtick, and the delimiter closes the body. Otherwise the body is read
# as shell, line by line (bash <<EOF, cat <<EOF | sh, ssh host <<EOF).
# If Python crashes, a plain regex over the raw command decides.
if printf '%s' "$COMMAND" | grep -Eq "${B}git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+commit([^[:alnum:]_-]|\$)"; then
  IFS= read -r -d '' COMMIT_PY <<'PYEOF'
import json, re, sys

data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
cmd = (data.get("tool_input") or {}).get("command") or ""
ps = data.get("tool_name") == "PowerShell"
esc = "`" if ps else "\\"
n = len(cmd)

DETECT = re.compile(r"\bgit(\s+-C\s+\S+)?\s+commit\b")
ALLOW = re.compile(r"\bcommit\b.*(\s--\s+[^\s-]|--only|--no-edit)")
SEP = re.compile(r"&&|\|\||[;&|]")
ENV_ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
LEADERS = {"sudo", "time", "nohup", "command", "builtin", "exec", "eval", "do", "then",
           "else", "elif", "if", "while", "until", "{", "(", "!", "&"}
PASSTHROUGH = {"cat", "tee"}
DATA = {"python", "python3", "py", "node", "git", "gh", "jq", "sqlite3", "psql", "mysql",
        "bq"} | PASSTHROUGH


def program(seg):
    """Name of the program a segment runs, without path and .exe, lowercase."""
    for tok in seg.replace("$(", " ").split():
        t = tok.lstrip("({`")
        if not t or ENV_ASSIGN.match(t) or t.lower() in LEADERS:
            continue
        name = t.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return name[:-4] if name.endswith(".exe") else name
    return ""


def consumer(text, pos):
    """Program consuming the body of the heredoc at text[pos]; cat/tee pass it down the pipe."""
    parts, start = [], 0
    for s in SEP.finditer(text):
        parts.append((start, s.start(), s.group()))
        start = s.end()
    parts.append((start, len(text), ""))
    k = next(j for j, (a, b, _) in enumerate(parts) if a <= pos <= b)
    while True:
        a, b, sep = parts[k]
        prog = program(text[a:b])
        if prog not in PASSTHROUGH or sep != "|" or k + 1 >= len(parts):
            return prog
        k += 1


def close_of(i, q, e):
    """Index after the quote q that closes the string; e escapes the next character."""
    while i < n:
        if e and cmd[i] == e:
            i += 2
        elif cmd[i] == q:
            return i + 1
        else:
            i += 1
    return n


def scan_dq(i):
    """Contents of "..." from i: (index after closing quote, shell text). $( ) is scanned as shell."""
    parts = []
    while i < n:
        c = cmd[i]
        if c == esc and i + 1 < n:
            parts.append(cmd[i:i + 2])
            i += 2
        elif c == '"':
            return i + 1, "".join(parts)
        elif not ps and cmd.startswith("$(", i) and not cmd.startswith("$((", i):
            i, _, sh = scan(i + 2, True)
            parts.append("$(" + sh + ")")
        else:
            parts.append(c)
            i += 1
    return n, "".join(parts)


def scan(i, in_subst):
    """(index, masked, shell) from i; in_subst: inside $( ), stops after the unmatched )."""
    masked, shell, line, heredocs = [], [], [], []
    depth = 0

    def emit(m, s=None):
        masked.append(m)
        line.append(m)
        shell.append(m if s is None else s)

    while i < n:
        c = cmd[i]
        if c == esc and i + 1 < n:
            emit("__", cmd[i:i + 2])
            i += 2
        elif c == "\n":
            emit("\n")
            i += 1
            text = "".join(line)
            line.clear()
            for delim, tabs, quoted, pos in heredocs:
                start, closed = i, False
                while i < n:
                    j = cmd.find("\n", i)
                    end = n if j < 0 else j
                    cur = cmd[i:end].rstrip("\r")
                    i = n if j < 0 else j + 1
                    if (cur.lstrip("\t") if tabs else cur) == delim:
                        closed = True
                        break
                body = cmd[start:i]
                expands = not quoted and ("$(" in body or "`" in body)
                if not closed or expands or consumer(text, pos) not in DATA:
                    i = start  # the body is shell: scan it line by line
                    break
            heredocs.clear()
        elif c == "#" and (not masked or masked[-1][-1] in " \t\n;&|("):
            j = cmd.find("\n", i)
            i = n if j < 0 else j
        elif in_subst and c == "(":
            depth += 1
            emit(c)
            i += 1
        elif in_subst and c == ")":
            if depth == 0:
                return i + 1, "".join(masked), "".join(shell)
            depth -= 1
            emit(c)
            i += 1
        elif ps and c == "@" and cmd[i + 1:i + 2] in ("'", '"'):
            q = cmd[i + 1]
            j = cmd.find("\n", i)
            if j >= 0 and cmd[i + 2:j].strip() == "":
                close = cmd.find("\n" + q + "@", j)
                k = n if close < 0 else close + 3
                emit("@" + q + "_" + q + "@", cmd[i:k])
                i = k
            else:
                emit(c)
                i += 1
        elif c == '"':
            k, sh = scan_dq(i + 1)
            emit('"_"', '"' + sh + '"')
            i = k
        elif c == "'" or (not ps and c == "$" and cmd[i + 1:i + 2] == "'"):
            s = i
            if c == "$":
                i += 1
            k = close_of(i + 1, "'", "\\" if c == "$" else None)
            emit("'_'", cmd[s:k])
            i = k
        elif not ps and cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            j = i + 2
            tabs = cmd.startswith("-", j)
            j += 1 if tabs else 0
            while j < n and cmd[j] in " \t":
                j += 1
            k = j
            while k < n and cmd[k] not in " \t\r\n;&|<>()":
                k += 1
            word = cmd[j:k]
            delim = "".join(ch for ch in word if ch not in "'\"\\")
            if delim:
                heredocs.append((delim, tabs, word != delim, sum(map(len, line))))
            emit(cmd[i:k])
            i = k
        else:
            emit(c)
            i += 1
    return n, "".join(masked), "".join(shell)


_, masked, shell = scan(0, False)
if not DETECT.search(shell):
    verdict = "ok"
else:
    segs = [s for s in re.split(r"[;&|\n]", masked) if DETECT.search(s)]
    verdict = "ok" if segs and all(ALLOW.search(s) for s in segs) else "deny"
sys.stdout.write(verdict)
PYEOF
  VERDICT=$(printf '%s' "$INPUT" | "$PY" -c "$COMMIT_PY" 2>/dev/null)
  if [ "$VERDICT" = deny ] || { [ "$VERDICT" != ok ] \
    && ! printf '%s' "$COMMAND" | grep -Eq "${B}commit([^[:alnum:]_;&|-][^;&|]*)?([[:space:]]--[[:space:]]+[^[:space:]-]|--only|--no-edit)"; }; then
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"git commit without paths commits the whole index, including files another session or agent staged. Use: git commit -m \"...\" -- path1 path2"}}'
    exit 0
  fi
fi
exit 0
