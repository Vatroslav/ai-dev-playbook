#!/usr/bin/env bash
# PreToolUse hook (matcher Bash): intent-based version bump guard for `git commit`.
#
# The bump follows the DECLARED INTENT of the commit (conventional-commit type), not the files:
#   source in the commit + no conventional type          -> deny ("declare intent")
#   feat / fix / perf / breaking + version line unchanged -> deny ("bump it in this commit")
#   docs / chore / style / refactor / test / ci / build / revert -> pass without a bump
#   message not readable (--no-edit, --amend, -C)         -> pass with a visible warning
# Model: feat -> minor, fix/perf -> patch, `type!:` or BREAKING CHANGE -> major.
# See docs/agent/versioning.md for the full model.
#
# It knows which files the commit will really contain:
#   git commit -m "..." -- a b      exactly a and b (staged or not; other staged files stay out)
#   git commit -m "..."             the index, plus files added by `git add` earlier in the same
#                                   command, plus tracked changes with -a / -am
# and reads the message from -m/--message (several -m allowed), -F/--file <path>,
# -F- with a heredoc, -m "$(cat <<'EOF' ... EOF)" and PowerShell here-strings (@'...'@).
#
# Fails CLOSED when no working Python exists (a guard that silently no-ops is worse than none,
# because everyone believes it is on). Works unchanged in Claude Code and Codex (JSON "deny").
#
# ---- per-repo configuration (Python regex syntax) ------------------------------------------
export VB_SOURCE_RE='^(src|app|lib|components|server)/'   # repo-relative paths that ship to users
export VB_VERSION_FILE='package.json'                     # repo-relative path of the version
export VB_VERSION_LINE_RE='^\+\s*"version"\s*:'           # an ADDED line in `git diff -U0` = bump
# Examples: VERSION + '^\+v?\d'  |  pyproject.toml + '^\+version\s*='
#           app/build.gradle.kts + '^\+\s*versionName'  (Android: also raise versionCode)
# ---------------------------------------------------------------------------------------------

INPUT=$(cat)
PY=''
for c in python python3 py; do   # first interpreter that actually RUNS (Windows has a python3 stub)
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then PY=$c; break; fi
done
if [ -z "$PY" ]; then
  if printf '%s' "$INPUT" | grep -Eq 'git([[:space:]]+-[cC][[:space:]]+[^[:space:]]+)*[[:space:]]+commit'; then
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Version guard cannot run: no working Python interpreter (tried python, python3, py). Install Python or fix PATH."}}'
  fi
  exit 0
fi

IFS= read -r -d '' VB_PY <<'PYEOF'
import json, os, re, shlex, subprocess, sys

data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
cmd = (data.get("tool_input") or {}).get("command") or ""
cwd = data.get("cwd") or os.getcwd()

if not re.search(r"(^|[^\w-])git(\s+-[cC]\s+\S+)*\s+commit(\W|$)", cmd):
    sys.exit(0)

SOURCE = re.compile(os.environ["VB_SOURCE_RE"])
VFILE = os.environ["VB_VERSION_FILE"]
VLINE = re.compile(os.environ["VB_VERSION_LINE_RE"])
PS = data.get("tool_name") == "PowerShell"
REDIR = re.compile(r"^\d*[<>]")
VALUE_LONG = {"--message", "--file", "--author", "--date", "--template", "--cleanup", "--trailer",
              "--fixup", "--squash", "--reuse-message", "--reedit-message", "--pathspec-from-file"}
VALUE_SHORT = set("mFCct")


def out(decision, reason):
    if decision == "warn":
        print(json.dumps({"systemMessage": "check-version-bump: " + reason}))
    else:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


def tokens(text):
    # newline is a command separator, not whitespace (multi-line commands)
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def is_sep(t):
    return bool(t) and all(ch in ";&|\n" for ch in t)


def git(where, *args):
    r = subprocess.run(["git", "-C", where, *args], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def lines(text):
    return [x for x in (text or "").splitlines() if x.strip()]


# ---- tokenize; on unbalanced quotes fall back to a crude regex for the message only ---------
try:
    toks = tokens(cmd)
except ValueError:
    m = re.search(r"""(?:-m|--message)[\s=]+(?:"([^"]*)"|'([^']*)'|(\S+))""", cmd)
    if not m:
        out("warn", "command could not be parsed, bump guard skipped - check the version manually.")
    toks = None
    fallback_msg = next(g for g in m.groups() if g is not None)

# ---- split into simple commands and find `git ... add` / `git ... commit` --------------------
adds, add_all = [], False
commit = None  # dict of what the commit invocation says
if toks is not None:
    segs, cur = [], []
    for t in toks:
        if is_sep(t):
            segs.append(cur)
            cur = []
        else:
            cur.append(t)
    segs.append(cur)
    for seg in segs:
        # stop at the first redirection: what follows is a heredoc body or a file name
        for i, t in enumerate(seg):
            if REDIR.match(t):
                seg = seg[:i]
                break
        if not seg or os.path.basename(seg[0]).lower() not in ("git", "git.exe"):
            continue
        i, where = 1, cwd
        while i < len(seg) and seg[i].startswith("-"):
            if seg[i] in ("-C", "-c") and i + 1 < len(seg):
                if seg[i] == "-C":
                    where = os.path.join(where, seg[i + 1])
                i += 2
            else:
                i += 1
        if i >= len(seg):
            continue
        sub, args = seg[i], seg[i + 1:]
        if sub == "add":
            for a in args:
                if a in ("-A", "--all", ".", "-u", "--update"):
                    add_all = True
                elif not a.startswith("-"):
                    adds.append(a)
        elif sub == "commit" and commit is None:
            c = {"where": where, "msgs": [], "file": None, "paths": [], "all": False,
                 "include": False, "no_edit": False, "amend": False, "reuse": False}
            j, dashdash = 0, False
            while j < len(args):
                a = args[j]
                nxt = args[j + 1] if j + 1 < len(args) else None
                if dashdash or not a.startswith("-") or a == "-":
                    c["paths"].append(a)
                elif a == "--":
                    dashdash = True
                elif a.startswith("--"):
                    name, eq, val = a.partition("=")
                    if name in VALUE_LONG and not eq:
                        val, j = nxt, j + 1
                    if name == "--message":
                        c["msgs"].append(val or "")
                    elif name == "--file":
                        c["file"] = val
                    elif name in ("--reuse-message", "--reedit-message", "--fixup", "--squash"):
                        c["reuse"] = True
                    elif name == "--all":
                        c["all"] = True
                    elif name == "--include":
                        c["include"] = True
                    elif name == "--no-edit":
                        c["no_edit"] = True
                    elif name == "--amend":
                        c["amend"] = True
                else:  # short flags, possibly combined: -am "msg", -mfoo, -F-
                    k = 1
                    while k < len(a):
                        ch = a[k]
                        if ch in VALUE_SHORT:
                            val = a[k + 1:]
                            if not val:
                                val, j = nxt, j + 1
                            if ch == "m":
                                c["msgs"].append(val or "")
                            elif ch == "F":
                                c["file"] = val
                            elif ch in "Cc":
                                c["reuse"] = True
                            break
                        if ch == "a":
                            c["all"] = True
                        elif ch == "i":
                            c["include"] = True
                        k += 1
                j += 1
            commit = c
    if commit is None:
        sys.exit(0)  # only mentioned (inside a string, a heredoc body, echo ...)
else:
    commit = {"where": cwd, "msgs": [fallback_msg], "file": None, "paths": [], "all": False,
              "include": False, "no_edit": False, "amend": False, "reuse": False}

# ---- which files does this commit contain? ----------------------------------------------------
top = git(commit["where"], "rev-parse", "--show-toplevel")
if top is None:
    sys.exit(0)  # not a repo
top = top.strip()
if git(top, "rev-parse", "--verify", "-q", "HEAD") is None:
    sys.exit(0)  # initial commit: nothing to compare against
prefix = (git(commit["where"], "rev-parse", "--show-prefix") or "").strip()


def rel(p):  # a path from the command (relative to the cwd) -> repo-relative pathspec
    if p.startswith(":"):
        return p
    p = p.replace("\\", "/")
    if os.path.isabs(p):
        try:
            return os.path.relpath(p, top).replace("\\", "/")
        except ValueError:
            return p
    return os.path.normpath(prefix + p).replace("\\", "/")


paths = [rel(p) for p in commit["paths"]]
inline = [rel(p) for p in adds]
if paths and not commit["include"]:
    # `git commit -- paths` commits the working-tree state of exactly these paths
    files = set(lines(git(top, "diff", "--name-only", "HEAD", "--", *paths))) | set(paths)
    vdiff_args = ["diff", "-U0", "HEAD", "--", VFILE]
    vf_in = VFILE in files
else:
    staged = set(lines(git(top, "diff", "--cached", "--name-only")))
    extra = set(inline) | set(paths)
    if add_all or commit["all"]:
        extra |= set(lines(git(top, "diff", "--name-only")))
    if add_all:
        extra |= set(lines(git(top, "ls-files", "--others", "--exclude-standard")))
    files = staged | extra
    vf_in = VFILE in files
    if VFILE in extra:
        vdiff_args = ["diff", "-U0", "HEAD", "--", VFILE]   # added in this same command
    else:
        vdiff_args = ["diff", "--cached", "-U0", "--", VFILE]

if not any(SOURCE.search(f) for f in files):
    sys.exit(0)  # no shipped source in this commit

# ---- the message ------------------------------------------------------------------------------
def heredoc_body(text, start=0):
    m = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w.-]*)\1[^\n]*\n").search(text, start)
    if not m:
        return None
    body = []
    for line in text[m.end():].split("\n"):
        if line.strip() == m.group(2):
            return "\n".join(body)
        body.append(line)
    return None


msg = None
if commit["msgs"]:
    parts = []
    for raw in commit["msgs"]:
        s = raw.strip()
        if s.startswith("$(") and "<<" in s:
            s = heredoc_body(s)  # -m "$(cat <<'EOF' ... EOF)": the body is the message
        elif len(s) >= 2 and s[0] == "@" and s[-1] == "@":  # PowerShell here-string @'...'@
            s = s[1:-1].strip("\r\n")
        elif not PS and ("$(" in s or "`" in s):
            s = None  # shell substitution: the real message is only known at run time
        if s is None:
            parts = None
            break
        parts.append(s)
    msg = "\n\n".join(parts) if parts is not None else None
elif commit["file"] is not None:
    if commit["file"] == "-":
        msg = heredoc_body(cmd, cmd.find("commit"))
    else:
        try:
            with open(os.path.join(commit["where"], commit["file"]), encoding="utf-8", errors="replace") as fh:
                msg = fh.read()
        except OSError:
            msg = None

if msg is None:
    if commit["no_edit"] or commit["amend"] or commit["reuse"]:
        out("warn", "commit message not readable from the command (--no-edit/--amend/-C) - bump guard "
                    "skipped, check the version manually.")
    out("deny", "This commit touches shipped source but its message cannot be read from the command. "
                "Pass it with -m \"type: subject\" (or -F <file>) so the guard can check the version bump.")

header = msg.strip().split("\n", 1)[0].strip()
m = re.match(r"^([A-Za-z]+)(\([^)]*\))?(!)?:\s", header)
ctype = m.group(1).lower() if m else ""
breaking = bool(m and m.group(3)) or bool(re.search(r"^BREAKING[ -]CHANGE:", msg, re.M))

bumped = vf_in and any(VLINE.search(x) for x in (git(top, *vdiff_args) or "").splitlines())

if breaking and not bumped:
    out("deny", f"Breaking change (type!: or BREAKING CHANGE) but {VFILE} is not bumped in this commit. "
                "Bump the MAJOR version and include the file in the commit.")
if ctype in ("feat", "fix", "perf"):
    if not bumped:
        out("deny", f"Type '{ctype}' changes shipped behaviour but {VFILE} is not bumped in this commit "
                    "(feat -> minor, fix/perf -> patch). Bump it and include it in the commit "
                    f"(e.g. git commit -m \"...\" -- <files> {VFILE}).")
elif ctype in ("docs", "chore", "style", "refactor", "test", "ci", "build", "revert"):
    pass
else:
    out("deny", "This commit touches shipped source but declares no intent. Start the message with a "
                "conventional type (feat/fix/perf/docs/chore/refactor/test/style/ci/build/revert, "
                "'type!:' for breaking) so the guard can decide whether a version bump is needed.")
PYEOF

printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "$VB_PY"
exit 0
