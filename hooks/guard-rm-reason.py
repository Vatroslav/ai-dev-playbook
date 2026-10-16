# -*- coding: utf-8 -*-
"""Decision engine for guard-rm.sh.

Reads one shell command on stdin. Prints an "ask" permission JSON (default, or --json) or the
plain reason text (--plain, used for agents without "ask" support) when the command really
deletes something that has no undo; prints nothing otherwise (exit 0 = decision made).
If this script crashes (exit != 0), guard-rm.sh falls back to a blunt grep that always asks.

Rules:
1. Fire only when rm/rmdir/Remove-Item/del/rd/ri/erase is the COMMAND: first token of a
   segment (split on &&, ||, ;, |, newline), after xargs/sudo, or find -exec/-delete.
   `grep "rm" file`, `echo rm`, `git rm` (tracked file = git is the undo) do NOT fire.
2. If ALL targets are temp, pass silently. Temp = basename starts with tmp/temp (tmp.py,
   tmp_build, temp-out.json), ends with .tmp/.temp, contains _tmp/-tmp/.tmp, lives in a
   folder named tmp/temp, or is inside the system temp dir (/tmp/x, $TMPDIR/x, $env:TEMP\\x,
   AppData\\Local\\Temp\\x, macOS /var/folders/../T/x). The temp root itself is NOT a temp
   target. Unknown targets ({} from xargs, empty, *, ., ~, /, bare variable) always ask.
3. Method deletes (.Delete(), ::DeleteFile()) are caught anywhere in a segment, and the
   payload of nested shells / eval (cmd /c, bash -c, powershell -Command, eval, iex) is
   analysed recursively with the same rules.
4. A heredoc body consumed by an interpreter or tool (python - <<'EOF', git commit -F- <<'EOF')
   is data, not shell, and is not scanned as shell lines.
5. Python/Node code that the command executes (heredoc body for python/node, python -c,
   node -e) is scanned for deletes in code (os.remove, shutil.rmtree, Path.unlink,
   fs.rmSync...) and for shell-from-code (os.system, subprocess.run), whose payload is
   scanned recursively.
6. Git is the undo: a target that is TRACKED by git and has no uncommitted changes, no untracked
   and no ignored files under it passes silently (git checkout/restore brings it back). Checked
   only for concrete paths (no globs, variables or ~), resolved against the session cwd
   (GUARD_RM_CWD, set by guard-rm.sh from the hook JSON). If the command changes directory
   (cd, pushd, Set-Location), relative targets are not trusted and ask. The repo root, an
   ancestor of it and anything inside .git always ask (deleting them deletes the undo).
   Disable with GUARD_RM_GIT_UNDO=0.

Known limits: a regex tokenizer, not a real shell parser. Pattern guards parse command text;
they are a speed bump, not a sandbox. Use a container or VM for a real boundary.
"""
import json
import os
import re
import subprocess
import sys

MAX_SEG = 90

DEL_CMDS = {'rm', 'rmdir', 'remove-item', 'del', 'erase', 'rd', 'ri'}
# Words that can stand in front of the real command in a segment.
LEADERS = {'sudo', 'time', 'nohup', 'command', 'builtin', 'exec', 'eval', 'do', 'then',
           'else', 'elif', 'if', 'while', 'until', '{', '(', '!', '&'}
# PowerShell parameters that carry a value - the value is a target (PATH) or not (VALUE).
PS_PATH_PARAMS = {'-path', '-literalpath', '-include', '-p', '-lp'}
PS_VALUE_PARAMS = {'-exclude', '-filter', '-erroraction', '-ea', '-warningaction', '-wa',
                   '-stream', '-credential', '-informationaction', '-ia',
                   '-errorvariable', '-ev', '-warningvariable', '-wv', '-outvariable', '-ov'}
FIND_NAME_OPTS = {'-name', '-iname', '-path', '-ipath', '-wholename', '-iwholename', '-regex', '-iregex'}

SEP = re.compile(r'&&|\|\||;|\|')
TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|\S+')
ENV_ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
REDIRECT = re.compile(r'^[0-9]*[<>]')
# Group 6 = the part below the temp root (empty for the root itself).
TEMP_ROOT = re.compile(
    r'^(/tmp|/var/tmp|(?:/private)?/var/folders/[^/]+/[^/]+/t'
    r'|[a-z]:/users/[^/]+/appdata/local/temp|/[a-z]/users/[^/]+/appdata/local/temp'
    r'|\$\{?(tmp|temp|tmpdir)\}?|\$env:(tmp|temp)|%(tmp|temp)%)(/(.+))?$')
TEMP_BASE = re.compile(r'^(tmp|temp)(?![a-z])|\.(tmp|temp)$|[._-](tmp|temp)(?![a-z])')
UNKNOWN = {'', '.', '..', '~', '*', '/', '.*', '**', '{}', '$_', '$f', '$file'}
# .NET / method deletes: [IO.File]::Delete(), [IO.Directory]::Delete(),
# VisualBasic FileSystem::DeleteFile/DeleteDirectory (also with SendToRecycleBin),
# $x.Delete(), (Get-Item x).Delete(). Target = first argument; empty or variable = unknown.
METHOD_DEL = re.compile(r'(::|\.)\s*delete(file|directory)?\s*\(\s*([^,)]*)', re.I)
# Nested shell / eval: the payload is analysed as its own command, up to MAX_DEPTH levels.
# cmd /c|/k rest of line; bash/sh/zsh/dash -c '...'; powershell/pwsh -Command|-c ...;
# eval / iex / Invoke-Expression '...'. Group 1 = payload.
NESTED = [re.compile(p, re.I | re.M) for p in (
    r'\bcmd(?:\.exe)?\s+/[ck]\s+("[^"]*"|.+$)',
    r'\b(?:ba|z|da)?sh(?:\.exe)?(?:\s+--?[a-z][\w-]*)*?\s+-[a-z]*c[a-z]*\s+("[^"]*"|\'[^\']*\'|\S+)',
    r'\b(?:powershell|pwsh)(?:\.exe)?(?:\s+\S+)*?\s+-c(?:ommand)?\s+("[^"]*"|\'[^\']*\'|.+$)',
    r'(?:^|[\s;&|({])(?:eval|iex|invoke-expression)\s+("[^"]*"|\'[^\']*\')',
)]
MAX_DEPTH = 3
# Heredoc: the body of `python - <<'EOF'` is Python, not shell, so its lines are not read as
# commands (`"rd": x` in a dict, `del d[k]`, a commit message mentioning "rm"). Skipped only
# when the receiver consumes the body itself (HEREDOC_CONSUMERS) and the shell executes
# nothing in the body (quoted delimiter, or no $( and no backtick). cat/tee pass the body on -
# the next pipe stage decides. Shell, ssh, docker exec, an unknown receiver and a heredoc
# without a closing delimiter are scanned line by line. NESTED still sees the whole text.
HEREDOC = re.compile(r'(?<!<)<<(-?)\s*(\'[^\'\n]*\'|"[^"\n]*"|\\?[A-Za-z_][\w.-]*)')
HEREDOC_CONSUMERS = {'python', 'python3', 'py', 'node', 'git', 'gh', 'jq', 'sqlite3', 'psql',
                     'mysql', 'bq'}
HEREDOC_PASSTHROUGH = {'cat', 'tee'}
# Deletes in code that the command executes. Code written to a file (cat > x.py) is not
# executed and not scanned. Target = first argument; only a string literal counts
# (also Path('x') in front of .unlink()); a variable or expression = unknown target.
CODE_RUNNERS = {'python', 'python3', 'py', 'node'}
CODE_DEL = re.compile(
    r'(?:\b(?:os\.(?:remove|unlink|rmdir|removedirs)|shutil\.rmtree|rmtree|send2trash'
    r'|rimraf(?:\.sync)?|(?:fs|fsp|promises)\.(?:rm|unlink|rmdir))'
    r'|\.(?:unlink|rmdir|rmSync|unlinkSync|rmdirSync))\s*\(\s*([^,)]*)')
# Shell from code: os.system("rm x"), subprocess.run(["rm", "-rf", x]) - payload goes to scan().
CODE_SHELL = re.compile(
    r'\b(?:os\.(?:system|popen)|subprocess\.(?:run|call|check_call|check_output|Popen)'
    r'|(?:child_process\.|(?<![\w.]))(?:exec|execSync|spawn|spawnSync))\s*\(\s*'
    r'(\[[^\]]*\]|"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`)')
CODE_INLINE = re.compile(
    r'\b(?:python3?|py|node)(?:\.exe)?["\']?(?:\s+-[^\s]+)*?\s+(?:-c|-e|--eval)(?=\s)', re.I)
PY_STR = re.compile(r'^[rRbBuU]?(["\'])(.*)\1$')
PATH_LIT = re.compile(r'Path\(\s*([rRbBuU]?(["\'])[^"\']*\2)\s*\)\s*$')


def unquote(t):
    if len(t) >= 2 and t[0] == t[-1] and t[0] in '"\'':
        return t[1:-1]
    return t


def clean_target(t):
    t = unquote(t.strip())
    t = t.lstrip('(`{').rstrip(')`}')
    return t.strip()


def is_temp(target):
    t = clean_target(target)
    if not t:
        return False
    low = t.replace('\\', '/').lower().rstrip('/')
    if low in UNKNOWN:
        return False
    m = TEMP_ROOT.match(low)
    if m:
        # inside the system temp root = temp; the root itself = not temp
        return bool(m.group(6))
    if low.startswith('$') and not low.startswith('$env:') and '/' not in low:
        return False  # bare variable ($f, $x) - unknown target
    parts = [p for p in low.split('/') if p]
    if not parts:
        return False
    # a tmp/temp folder above the target (tmp/x.py, ./temp/*, ~/tmp/foo)
    if any(p in ('tmp', 'temp') for p in parts[:-1]):
        return True
    return bool(TEMP_BASE.search(parts[-1]))


# Context for the git-undo check (rule 6); filled in main().
CTX = {'cd': False, 'cwd': None}
CD_CMD = re.compile(r'(?:^|[;&|\n({])\s*(?:cd|pushd|popd|chdir|set-location|sl)(?:\s|$)', re.I)
NOT_CONCRETE = re.compile(r'[*?\[\]{}$`%~]')


def _git(cwd, *args):
    try:
        r = subprocess.run(['git', '-C', cwd, *args], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', 'replace')


def git_restorable(target):
    # True when git can bring the target back exactly as it is now (rule 6).
    if os.environ.get('GUARD_RM_GIT_UNDO', '1') == '0':
        return False
    t = clean_target(target)
    if not t or t.lower() in UNKNOWN or t.startswith('-') or NOT_CONCRETE.search(t):
        return False
    t = t.replace('\\', '/')
    m = re.match(r'^/([a-zA-Z])/(.*)$', t)
    if os.name == 'nt' and m:  # MSYS path /c/x -> c:/x
        t = m.group(1) + ':/' + m.group(2)
    if not os.path.isabs(t):
        if CTX['cd']:
            return False
        t = os.path.join(CTX['cwd'] or os.getcwd(), t)
    full = os.path.normpath(t)
    if not os.path.lexists(full):
        return False
    start = full if os.path.isdir(full) else os.path.dirname(full)
    top = _git(start, 'rev-parse', '--show-toplevel')
    if not top:
        return False
    norm = lambda x: os.path.normcase(os.path.realpath(x))
    top_n, full_n = norm(top.strip()), norm(full)
    if not full_n.startswith(top_n.rstrip(os.sep) + os.sep):
        return False  # the repo root itself, an ancestor of it, or outside via a symlink
    rel = os.path.relpath(full_n, top_n).replace(os.sep, '/')
    if '.git' in rel.split('/'):
        return False
    top_s = top.strip()
    if not _git(top_s, 'ls-files', '--', rel):
        return False  # not tracked
    status = _git(top_s, 'status', '--porcelain', '--ignored', '--untracked-files=all', '--', rel)
    return status == ''


def is_safe(target):
    return is_temp(target) or git_restorable(target)


def tokenize(seg):
    return [m.group(0) for m in TOKEN.finditer(seg)]


def targets_after(tokens, i, powershell):
    # Targets of the command starting at tokens[i]; skips flags and redirections.
    out = []
    j = i + 1
    end_of_flags = False
    while j < len(tokens):
        t = tokens[j]
        raw = unquote(t)
        lowt = raw.lower()
        if raw == '--' and not end_of_flags:
            end_of_flags = True
        elif not end_of_flags and raw.startswith('-') and len(raw) > 1:
            if powershell and lowt in PS_PATH_PARAMS and j + 1 < len(tokens):
                j += 1
                out.extend(x for x in unquote(tokens[j]).split(',') if x.strip())
            elif powershell and lowt in PS_VALUE_PARAMS and j + 1 < len(tokens):
                j += 1
        elif REDIRECT.match(raw):
            if re.match(r'^[0-9]*(>>?|<)$', raw) and j + 1 < len(tokens):
                j += 1  # bare `>` / `2>` - also skip the file name
        elif raw in ('\\;', '\\', '+'):
            pass
        else:
            if powershell:
                out.extend(x for x in raw.split(',') if x.strip())
            else:
                out.append(raw)
        j += 1
    return out


def find_targets(tokens):
    # find: -name/-path values decide what is deleted; without them, the search roots.
    names = []
    roots = []
    j = 1
    while j < len(tokens):
        t = unquote(tokens[j])
        if t.startswith('-') or t in ('(', '!', '\\('):
            if t.lower() in FIND_NAME_OPTS and j + 1 < len(tokens):
                names.append(unquote(tokens[j + 1]))
                j += 1
        elif not names and not any(unquote(x).startswith('-') for x in tokens[1:j]):
            roots.append(t)
        j += 1
    return names or roots


def command_tokens(seg):
    # (tokens, index of the real command) - skips env assignments, sudo/eval/do... and `$(`.
    # Split `$(` from the command so that x=$(rm foo) and $(rm foo) put rm in command position.
    tokens = tokenize(seg.replace('$(', ' $( '))
    i = 0
    while i < len(tokens):
        t = unquote(tokens[i])
        if t.startswith('$('):
            t = t[2:]
        t = t.lstrip('(`{')
        if not t or ENV_ASSIGN.match(t) or t.lower() in LEADERS:
            i += 1
            continue
        break
    return tokens, i


def analyze_segment(seg):
    # Returns (token, targets) if the segment is a delete, else None.
    m = METHOD_DEL.search(seg)
    if m:
        arg = m.group(3).strip()
        return m.group(0).split('(')[0].strip(), [arg] if arg else []
    tokens, i = command_tokens(seg)
    if i >= len(tokens):
        return None
    cmd = unquote(tokens[i]).lstrip('(`{')
    cmd_low = cmd.lower()
    if cmd_low in DEL_CMDS:
        ps = cmd_low not in ('rm', 'rmdir') or any(
            unquote(x).lower() in ('-recurse', '-force', '-path', '-literalpath') for x in tokens)
        return cmd, targets_after(tokens, i, ps)
    if cmd_low == 'xargs':
        for j in range(i + 1, len(tokens)):
            if unquote(tokens[j]).lower() in DEL_CMDS:
                return unquote(tokens[j]), []  # targets come through the pipe - unknown
    if cmd_low == 'find':
        lows = [unquote(x).lower() for x in tokens]
        if '-delete' in lows:
            return 'find -delete', find_targets(tokens)
        for j, x in enumerate(lows):
            if x in ('-exec', '-execdir', '-ok', '-okdir') and j + 1 < len(lows) and lows[j + 1] in DEL_CMDS:
                return 'find -exec ' + lows[j + 1], find_targets(tokens)
    return None


def program(seg):
    # Name of the program a segment runs, without path and .exe, lowercase.
    tokens, i = command_tokens(seg)
    if i >= len(tokens):
        return ''
    name = unquote(tokens[i]).lstrip('(`{').replace('\\', '/').rsplit('/', 1)[-1].lower()
    return name[:-4] if name.endswith('.exe') else name


def heredoc_consumer(line, pos):
    # Program that consumes the body of the heredoc whose operator is at line[pos];
    # cat/tee pass it on down the pipe. '' when the pipe continues on the next line.
    segs = []  # (start, end, separator after the segment)
    start = 0
    for s in SEP.finditer(line):
        segs.append((start, s.start(), s.group(0)))
        start = s.end()
    segs.append((start, len(line), ''))
    k = next(j for j, (a, b, _) in enumerate(segs) if a <= pos <= b)
    while True:
        a, b, sep = segs[k]
        prog = program(line[a:b])
        if prog not in HEREDOC_PASSTHROUGH or sep != '|':
            return prog
        if k + 1 >= len(segs):
            return ''
        k += 1


def after_heredocs(lines, n):
    # (index of the next line, [(first line, code)] for bodies executed by python/node).
    # The index skips bodies when they are all data, otherwise n + 1 (bodies scanned as lines).
    line = lines[n]
    nxt = n + 1
    code = []
    for m in HEREDOC.finditer(line):
        raw = m.group(2)
        quoted = raw[0] in '\'"\\'
        delim = raw[1:-1] if raw[0] in '\'"' else raw.lstrip('\\')
        end = nxt
        while end < len(lines):
            cand = lines[end].rstrip('\r')
            if (cand.lstrip('\t') if m.group(1) else cand) == delim:
                break
            end += 1
        body = '\n'.join(lines[nxt:end])
        prog = heredoc_consumer(line, m.start())
        if prog in CODE_RUNNERS:
            code.append((nxt + 1, body))
        if end >= len(lines):
            return n + 1, code  # no closing delimiter
        expands = not quoted and ('$(' in body or '`' in body)
        if expands or prog not in HEREDOC_CONSUMERS | HEREDOC_PASSTHROUGH:
            return n + 1, code
        nxt = end + 1
    return nxt, code


def make_hit(tok, text, n, multiline, via, targets):
    text = text.strip()
    if len(text) > MAX_SEG:
        text = text[:MAX_SEG] + '...'
    where = ' (line %d)' % n if multiline else ''
    if via:
        where += ' (via %s)' % via
    bad = [clean_target(x) for x in targets if not is_safe(x)]
    return {'token': tok, 'where': where, 'text': text, 'targets': bad}


def code_targets(code, m):
    # Delete target in code: string literal as first argument, or Path('x') before .unlink().
    arg = m.group(1).strip()
    if not arg and m.group(0).startswith('.'):
        p = PATH_LIT.search(code[:m.start()])
        arg = p.group(1) if p else ''
    s = PY_STR.match(arg)
    return [s.group(2)] if s else []


def inline_code(text, start):
    # (offset, code) after `python -c` / `node -e`: quoted string, PowerShell here-string,
    # or the rest of the line.
    off = start + len(text[start:]) - len(text[start:].lstrip(' \t'))
    s = text[off:]
    if s[:2] in ("@'", '@"'):
        end = s.find('\n' + s[1] + '@')
        return off + 2, s[2:] if end < 0 else s[2:end]
    if s[:1] in ('"', "'"):
        j = 1
        while j < len(s) and s[j] != s[0]:
            j += 2 if s[j] == '\\' else 1
        return off + 1, s[1:j]
    return off, s.split('\n', 1)[0]


def scan_code(code, first, multiline, via, depth):
    # Hits in Python/Node code; `first` = line of the command where the code starts.
    hits = []
    for m in CODE_DEL.finditer(code):
        targets = code_targets(code, m)
        if targets and all(is_safe(x) for x in targets):
            continue
        a = code.rfind('\n', 0, m.start()) + 1
        text = code[a:].split('\n', 1)[0]
        hits.append(make_hit(m.group(0).split('(')[0].strip(), text,
                             first + code.count('\n', 0, m.start()), multiline, via, targets))
    if depth < MAX_DEPTH:
        for m in CODE_SHELL.finditer(code):
            arg = m.group(1)
            if arg.startswith('['):
                payload = ' '.join(x for _, x in re.findall(r'(["\'])(.*?)\1', arg))
            else:
                payload = arg[1:-1]
            hits.extend(scan(payload, depth + 1, m.group(0).split('(')[0].strip()))
    return hits


def scan(cmd_text, depth=0, via=''):
    # Hits for the whole command text; nested shell/eval payloads recursively.
    multiline = '\n' in cmd_text.strip()
    hits = []
    lines = cmd_text.split('\n')
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        n = idx + 1
        idx, code = after_heredocs(lines, idx)
        for first, body in code:
            hits.extend(scan_code(body, first, multiline, via, depth))
        pos = 0
        pieces = []
        for s in SEP.finditer(line):
            pieces.append(line[pos:s.start()])
            pos = s.end()
        pieces.append(line[pos:])
        for seg in pieces:
            res = analyze_segment(seg)
            if not res:
                continue
            tok, targets = res
            if targets and all(is_safe(x) for x in targets):
                continue
            hits.append(make_hit(tok, seg, n, multiline, via, targets))
    for m in CODE_INLINE.finditer(cmd_text):
        off, code = inline_code(cmd_text, m.end())
        hits.extend(scan_code(code, cmd_text.count('\n', 0, off) + 1, multiline, via, depth))
    if depth < MAX_DEPTH:
        for rx in NESTED:
            for m in rx.finditer(cmd_text):
                wrapper = ' '.join(cmd_text[m.start():m.start(1)].strip(' ;&|({').split())
                hits.extend(scan(unquote(m.group(1).strip()), depth + 1, wrapper))
    return hits


def fmt(h):
    target = (' [target: %s]' % ', '.join(h['targets'])) if h['targets'] else ' [target unknown]'
    return '"%s"%s: %s%s' % (h['token'], h['where'], h['text'], target)


def main():
    text = sys.stdin.read()
    CTX['cd'] = bool(CD_CMD.search(text))
    CTX['cwd'] = os.environ.get('GUARD_RM_CWD') or None
    found = scan(text)
    if not found:
        return
    shown, counts = [], {}
    for e in (fmt(h) for h in found):
        if e in counts:
            counts[e] += 1
        else:
            counts[e] = 1
            shown.append(e)
    shown = [e if counts[e] == 1 else '%s (%dx)' % (e, counts[e]) for e in shown]
    reason = 'Delete with no undo (not temp, not a clean tracked file) - triggered by: ' + ' | '.join(shown)
    if '--plain' in sys.argv[1:]:
        print(reason)
        return
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'ask',
            'permissionDecisionReason': reason,
        }
    }))


if __name__ == '__main__':
    main()
