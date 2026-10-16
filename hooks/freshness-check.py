"""SessionStart hook: freshness of verified notes (frontmatter fields `verified`, `stale_after`).

Prints into the agent's context the markdown files of the current repo whose `stale_after`
date has passed, or whose body changed after the last verification. Prints nothing when all is
fresh. Never blocks, only reads (git + markdown).

Convention - only files that make claims about an EXTERNAL system (a SaaS API, the DB schema,
a deployed app, a vendor's pricing) get these fields, and only when someone actually checked live:

    ---
    verified:
      - by: agent/<model>           # or human:<name>
        at: YYYY-MM-DDTHH:MM:SS+00:00
        how: GET /v1/lists on the email provider API (read-only)
    stale_after: YYYY-MM-DDT00:00:00+00:00   # set by how fast that system changes
    ---

Reading a note is not verification and is never recorded. The edit date is not recorded - git
has it. In SKILL.md put the fields under `metadata:` (some skill uploaders reject unknown
top-level keys).

"Changed after verification" is computed from commits, not timestamps: the last commit that
changed `verified` is the verification. If a later commit (or an uncommitted edit) changed the
BODY, the verification no longer covers the content. Frontmatter-only edits (e.g. a new
`stale_after`) do not invalidate it. A rename breaks history (no --follow).

Register in ~/.claude/settings.json (see hooks/claude-settings.user.example.json):
  "SessionStart": [{"hooks": [{"type": "command", "command": "python ~/.claude/hooks/freshness-check.py"}]}]
Usage outside the hook: python freshness-check.py [path inside a repo]
Keep it in ~/.claude/hooks (outside any repo the agent edits freely): code that runs by itself
at every session start is exactly what an injected instruction would want to rewrite.
Requires PyYAML (pip install pyyaml). Without it the hook prints one line saying so instead of
silently checking nothing.
"""
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

try:
    import yaml
except ImportError:  # fail visibly: a silent no-op looks exactly like "everything is fresh"
    print("freshness-check: PyYAML is not installed (pip install pyyaml) - verified notes were NOT checked.")
    sys.exit(0)

MAX_LINES = 20
MAX_COMMITS = 200
KEYS = ("verified:", "stale_after:")
BROKEN = object()


def git(repo, *args):
    r = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=repo, capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


def split(text):
    """(frontmatter dict or None, body). Invalid YAML raises yaml.YAMLError/ValueError."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[0].rstrip() != "---":
        return None, "\n".join(lines).strip()
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            fm = yaml.safe_load("\n".join(lines[1:i])) or {}
            if not isinstance(fm, dict):
                raise ValueError("frontmatter is not a mapping")
            return fm, "\n".join(lines[i + 1:]).strip()
    return None, "\n".join(lines).strip()


def fields(fm):
    """`verified` and `stale_after` from the top of the frontmatter or under `metadata`."""
    fm = fm or {}
    meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    return {k: fm[k] if k in fm else meta[k] for k in ("verified", "stale_after") if k in fm or k in meta}


def load(text):
    """(verified, body) of one version of a file."""
    try:
        fm, body = split(text)
    except (yaml.YAMLError, ValueError):
        return BROKEN, text
    return fields(fm).get("verified"), body


def to_dt(v):
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            return to_dt(datetime.fromisoformat(v.strip()))
        except ValueError:
            return None
    return None


def last_verified(verified):
    entries = verified if isinstance(verified, list) else [verified]
    dates = [to_dt(e.get("at")) for e in entries if isinstance(e, dict)]
    dates = [d for d in dates if d]
    return f"{max(dates):%Y-%m-%d}" if dates else "no date"


def changed_after(repo, rel, verified, body):
    head = git(repo, "show", f"HEAD:{rel}")
    if head is None:
        return None  # file not committed yet
    head_verified, head_body = load(head)
    if verified != head_verified:
        return None  # verification just written, not committed yet
    if body != head_body:
        return f"content edited after the last verification ({last_verified(verified)}), not committed yet"
    newest_change = None
    log = git(repo, "log", f"-{MAX_COMMITS}", "--format=%H %cI", "--", rel) or ""
    for line in log.splitlines():
        sha, when = line.split(" ", 1)
        cur_verified, cur_body = load(git(repo, "show", f"{sha}:{rel}") or "")
        prev = git(repo, "show", f"{sha}^:{rel}")
        if prev is None:
            break  # file creation (or rename)
        prev_verified, prev_body = load(prev)
        if cur_verified != prev_verified:
            break  # the verification commit
        if cur_body != prev_body and newest_change is None:
            newest_change = when[:10]
    if newest_change:
        return f"content changed {newest_change}, last verification {last_verified(verified)}"
    return None


def check(path, now, repo, rel):
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---") or not any(k in text for k in KEYS):
        return []
    try:
        fm, body = split(text)
    except (yaml.YAMLError, ValueError):
        return ["frontmatter cannot be parsed"]
    f = fields(fm)
    msgs = []
    if "stale_after" in f:
        stale = to_dt(f["stale_after"])
        if stale is None:
            msgs.append("stale_after is not a date")
        elif now >= stale:
            msgs.append(f"stale since {stale:%Y-%m-%d}")
    if "verified" in f:
        msg = changed_after(repo, rel, f["verified"], body)
        if msg:
            msgs.append(msg)
    return msgs


def main():
    start = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    top = git(start, "rev-parse", "--show-toplevel")
    if not top:
        return
    repo = Path(top.strip())
    now = datetime.now(timezone.utc)
    out = []
    for rel in filter(None, (git(repo, "ls-files", "-z", "--", "*.md") or "").split("\0")):
        if (repo / rel).is_file():
            out += [f"- {rel}: {m}" for m in check(repo / rel, now, repo, rel)]
    if out:
        print(f"Freshness of verified notes in {repo.name} (frontmatter verified/stale_after):")
        print("\n".join(out[:MAX_LINES]))
        if len(out) > MAX_LINES:
            print(f"- ... and {len(out) - MAX_LINES} more")
        print("Claims in these files are notes, not verified state: check live before relying on "
              "them, then renew `verified`.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a hook must never break session start
        print(f"freshness-check: error ({type(e).__name__}: {e})")
