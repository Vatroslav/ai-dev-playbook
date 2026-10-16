#!/usr/bin/env python
"""decision_capture.py - deterministic half of the /decision-capture skill (optional, advanced).

Reads local Claude Code transcripts for the repos listed in repos.json, strips them down to
USER and ASSISTANT text, and hands the stripped files to a subagent (the judgment half, run by
the skill). Then appends the confirmed decisions to the repo's log. It never touches git: the
skill commits the log through the repo's normal workflow.

Files (all relative to the skill folder):
  repos.json                  opt-in list of repos (committed)
  state/<repo>.json           last seen timestamp per session (local, gitignored)
  state/<repo>.pending.json   new state from the last scan, promoted only by `append`
  out/<repo>/<session8>.md    stripped transcripts (local, gitignored)

Commands:
  scan [--since-hours N]   For each repo, walk its transcript folders (main checkout + worktrees).
                           For every session with new USER turns since the last run, write a
                           stripped dialogue. Tool calls/results, thinking and system reminders are
                           dropped: they are most of the volume and the main prompt-injection surface.
                           If the session has older turns, MARKER goes before the first new one.
                           Sessions that start with a slash command listed in "skip_commands" are
                           skipped. Prints JSON [{repo, log, sessions, skipped}].
                           A repo with no state starts from the last N hours (default 24).
  append <repo> [file]     If file has decisions: append "## YYYY-MM-DD" + file to the repo's log.
                           Always promote the pending state (so the next scan starts after this one).
                           Without a successful `append`, the next scan re-processes the same turns,
                           deliberately, so a crashed run loses nothing.
  strip <jsonl> [out]      Strip one transcript, for testing the extractor prompt by hand.

Environment: DECISION_CAPTURE_PROJECTS overrides the transcript root (~/.claude/projects).
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codepage
except (AttributeError, OSError):
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG = SKILL_DIR / "repos.json"
STATE_DIR = SKILL_DIR / "state"
OUT_ROOT = SKILL_DIR / "out"
PROJECTS = Path(os.environ.get("DECISION_CAPTURE_PROJECTS", "~/.claude/projects")).expanduser()
MARKER = "--- NEW SINCE LAST RUN - record only decisions confirmed BELOW this line ---"
NONE = "No decisions."

STRIP_TAGS = [
    r"<system-reminder>.*?</system-reminder>",
    r"<local-command-caveat>.*?</local-command-caveat>",
    r"<local-command-stdout>.*?</local-command-stdout>",
    r"<command-name>.*?</command-name>",
    r"<command-message>.*?</command-message>",
    r"<command-args>.*?</command-args>",
    r"<task-notification>.*?</task-notification>",
]
TAG_RE = re.compile("|".join(STRIP_TAGS), re.DOTALL)
COMMAND_RE = re.compile(r"<command-name>/?([\w:.-]+)</command-name>")


def load_config():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return Path(cfg.get("root", "~/code")).expanduser(), cfg["repos"]


def repo_cfg(name):
    root, repos = load_config()
    for r in repos:
        if r["name"] == name:
            return root, r
    sys.exit(f"repo '{name}' is not in {CONFIG}")


def project_dirs(repo: Path):
    # Claude Code keeps transcripts in ~/.claude/projects/<slug>/, where slug is the absolute repo
    # path with every non-alphanumeric character replaced by "-"; worktree sessions get
    # "<slug>--claude-worktrees-*". Check this once against your own ~/.claude/projects listing.
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    dirs = [PROJECTS / slug] + sorted(PROJECTS.glob(slug + "--claude-worktrees-*"))
    return [d for d in dirs if d.is_dir()]


def raw_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # tool_result blocks have no "text" type -> dropped
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def read_session(path: Path):
    """Return (turns, first_command); turns = [(ts_iso, who, text)], who in USER|ASSISTANT|SCHEDULED."""
    turns, first_command, seen_user = [], None, False
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            if t not in ("user", "assistant") or d.get("isMeta") or d.get("isSidechain"):
                continue
            raw = raw_text((d.get("message") or {}).get("content"))
            if t == "user" and not seen_user and raw.strip():
                seen_user = True
                m = COMMAND_RE.search(raw)
                first_command = m.group(1) if m else None
            text = TAG_RE.sub("", raw).strip()
            if not text:
                continue
            who = "ASSISTANT" if t == "assistant" else ("SCHEDULED" if text.startswith("<scheduled-task") else "USER")
            turns.append((d.get("timestamp") or "", who, text))
    return turns, first_command


def local_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts[:16].replace("T", " ")


def render(sid, repo, turns, marker_at):
    out = [f"# Transcript {sid}", f"repo: {repo}", f"turns: {len(turns)}", ""]
    for i, (ts, who, text) in enumerate(turns):
        if marker_at is not None and i == marker_at:
            out += [MARKER, ""]
        out += [f"### {who} [{local_ts(ts)}]", text, ""]
    return "\n".join(out)


def load_state(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sessions": {}}


def scan_repo(root, cfg, cutoff):
    name = cfg["name"]
    repo = root / name
    skip = set(cfg.get("skip_commands", []))
    sessions = load_state(STATE_DIR / f"{name}.json").get("sessions", {})
    bootstrap = not sessions
    out_dir = OUT_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.md"):
        old.unlink()
    pending = {"sessions": dict(sessions), "last_run": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    result = {"repo": name, "log": str(repo / cfg["log"]), "sessions": [], "skipped": 0}
    dirs = project_dirs(repo)
    if not dirs:
        result["error"] = f"no transcript folder for {repo}"
    for pdir in dirs:
        for jsonl in sorted(pdir.glob("*.jsonl")):
            sid = jsonl.stem
            turns, first_command = read_session(jsonl)
            if not turns:
                continue
            last_seen = sessions.get(sid) or (cutoff if bootstrap else "")
            new_idx = [i for i, (ts, _, _) in enumerate(turns) if ts > last_seen]
            pending["sessions"][sid] = max(ts for ts, _, _ in turns)
            new_user = sum(1 for i in new_idx if turns[i][1] == "USER")
            if not new_user:
                continue
            if first_command in skip:
                result["skipped"] += 1
                continue
            first_new = new_idx[0]
            out = out_dir / f"{sid[:8]}.md"
            out.write_text(render(sid, repo, turns, first_new if first_new > 0 else None), encoding="utf-8")
            result["sessions"].append({"session": sid[:8], "file": str(out),
                                       "new_turns": len(new_idx), "new_user_turns": new_user})
    (STATE_DIR / f"{name}.pending.json").write_text(json.dumps(pending, indent=2), encoding="utf-8")
    return result


def cmd_scan(since_hours):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    root, repos = load_config()
    print(json.dumps([scan_repo(root, cfg, cutoff) for cfg in repos], indent=2))


def cmd_append(name, src):
    root, cfg = repo_cfg(name)
    log = root / name / cfg["log"]
    pending = STATE_DIR / f"{name}.pending.json"
    if not pending.exists():
        sys.exit(f"{name}: no {pending.name} - run scan first")
    body = src.read_text(encoding="utf-8").strip() if src and src.exists() else ""
    if body == NONE:
        body = ""
    if body and not log.exists():
        sys.exit(f"{name}: log {log} missing - create it (with its header) before the first entry")
    if body:
        current = log.read_text(encoding="utf-8")
        sep = "" if current.endswith("\n") else "\n"
        log.write_text(f"{current}{sep}\n## {date.today().isoformat()}\n\n{body}\n", encoding="utf-8")
    pending.replace(STATE_DIR / f"{name}.json")
    if not body:
        print(f"{name}: no decisions, state acknowledged")
        return
    n_dec = len(re.findall(r"^- \*\*\[", body, re.MULTILINE))
    n_ses = len(set(re.findall(r"\(session (\w{8})\)", body)))
    print(f"{name}: appended {n_dec} decision(s) from {n_ses} session(s) to {cfg['log']} - commit it with the repo's normal workflow")


def cmd_strip(src, dst):
    turns, _ = read_session(src)
    out = dst or (OUT_ROOT / f"{src.stem[:8]}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(src.stem, src.parent, turns, None), encoding="utf-8")
    print(f"{out} ({len(turns)} turns)")


def main():
    a = sys.argv[1:]
    if a[:1] == ["scan"]:
        cmd_scan(int(a[a.index("--since-hours") + 1]) if "--since-hours" in a else 24)
    elif a[:1] == ["append"] and len(a) >= 2:
        cmd_append(a[1], Path(a[2]) if len(a) > 2 else None)
    elif a[:1] == ["strip"] and len(a) >= 2:
        cmd_strip(Path(a[1]), Path(a[2]) if len(a) > 2 else None)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
