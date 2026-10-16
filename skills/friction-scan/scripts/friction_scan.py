#!/usr/bin/env python
"""friction_scan.py - extract friction candidates from Claude Code transcripts.

The script does NOT classify and does NOT write the log. It only extracts candidates
deterministically from ~/.claude/projects/*/*.jsonl; a model reviews the output, classifies,
and appends real friction to the friction log. Promotion of a recurring pattern into a rule
goes through a human yes/no per item - never automatic (a bad rule silently degrades every
future session; an extra line in the log costs nothing).

Transcripts live on each developer's machine, so each developer runs this on their own
sessions. Only summaries (never quotes) go into the shared friction log.

Candidate kinds:
  hard  - the human interrupted a run or rejected a tool call. Near-zero false positives,
          used as the calibration anchor. The next human prompt is attached as "explanation".
  soft  - an ordinary human prompt after an agent reply. Most are NOT friction; the model decides.

Examples:
  python friction_scan.py --since 30
  python friction_scan.py --since 7 --repo my-app --format json
  python friction_scan.py --commit-state          # next run starts where this one ended

Environment overrides:
  FRICTION_PROJECTS_DIR   transcript root (default ~/.claude/projects)
  FRICTION_STATE_PATH     state file (default ~/.claude/friction-state.json)
  FRICTION_REPOS_DIR      name of the folder that holds your repos (default "projects")
  FRICTION_PROMPT_SOURCES comma list of promptSource values that mark a human-typed prompt
                          (default "sdk"); "any" accepts every non-meta user text turn

Transcript format notes (verify against your own client - fields differ between versions):
  - toolDenialKind on a tool_result: "user-rejected" = human clicked deny. Other values
    (permission-rule, automode-blocked, ...) are policy, not human friction.
  - promptSource on a user message: in the desktop app human-typed prompts carry "sdk",
    system notices carry "system". Other clients may omit the field; if --kind soft finds
    nothing at all, check one transcript and set FRICTION_PROMPT_SOURCES.
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

PROJECTS = os.path.expanduser(os.environ.get("FRICTION_PROJECTS_DIR", "~/.claude/projects"))
STATE_PATH = os.path.expanduser(os.environ.get("FRICTION_STATE_PATH", "~/.claude/friction-state.json"))

# Project folders are the session cwd with separators replaced by '-', e.g.
# C--Users-<name>-projects-my-app or -home-<name>-projects-my-app. Keep the tail after the
# repos root folder name; adjust REPOS_DIR to the folder that holds your repos.
REPOS_DIR = os.environ.get("FRICTION_REPOS_DIR", "projects")
REPO_RE = re.compile(r"^.*?-" + re.escape(REPOS_DIR) + r"-(.+)$")
WORKTREE_RE = re.compile(r"--claude-worktrees-.*$")
CMD_RE = re.compile(r"<command-name>")
INTERRUPT_MARK = "interrupted by user"
HARD_DENIALS = {"user-rejected", "cancelled"}
_SOURCES = os.environ.get("FRICTION_PROMPT_SOURCES", "sdk").strip()
HUMAN_PROMPT_SOURCES = None if _SOURCES == "any" else {s.strip() for s in _SOURCES.split(",") if s.strip()}
PROMPT_CHARS = 220
CONTEXT_CHARS = 180


def repo_name(dirname):
    m = REPO_RE.match(dirname)
    name = m.group(1) if m else dirname
    return WORKTREE_RE.sub("", name)


def clean_skill(sk):
    """A skill from a worktree arrives as '.claude/worktrees/x:name' - keep the name."""
    if not sk:
        return None
    return sk.rsplit(":", 1)[-1].strip() or None


def text_of(content):
    """Join the text blocks of a message; tool_result blocks and images are skipped."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def is_tool_result(content):
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def parse_ts(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def flatten(s, limit, tail=False):
    s = re.sub(r"\s+", " ", s or "").strip()
    if len(s) <= limit:
        return s
    return ("..." + s[-limit:]) if tail else (s[:limit] + "...")


def candidate(o, path, repo, skill, kind, signal, prompt, context):
    return {"ts": o.get("timestamp", ""), "repo": repo, "session": os.path.basename(path)[:8],
            "skill": skill or "-", "kind": kind, "signal": signal, "prompt": prompt,
            "after": "", "context": flatten(context, CONTEXT_CHARS, tail=True)}


def scan_file(path, repo, since):
    found = []
    pending = []          # hard signals waiting for the human's explanation
    current_skill = None
    last_assistant = ""
    seen_assistant = False
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return found
    with fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("isSidechain"):
                continue  # subagent traffic
            kind = o.get("type")
            if kind == "assistant":
                for b in o.get("message", {}).get("content", []) or []:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use" and b.get("name") == "Skill":
                        current_skill = clean_skill((b.get("input") or {}).get("skill")) or current_skill
                    elif b.get("type") == "text" and b.get("text", "").strip():
                        last_assistant = b["text"]
                        seen_assistant = True
                continue
            if kind != "user":
                continue
            content = o.get("message", {}).get("content")
            if is_tool_result(content):
                if o.get("toolDenialKind") in HARD_DENIALS:
                    pending.append(len(found))
                    found.append(candidate(o, path, repo, current_skill, "hard",
                                           o.get("toolDenialKind"), "", last_assistant))
                continue
            if o.get("isMeta"):
                continue
            ts = parse_ts(o.get("timestamp"))
            if since and ts and ts < since:
                continue
            txt = text_of(content)
            if not txt.strip():
                continue
            if INTERRUPT_MARK in txt:
                pending.append(len(found))
                found.append(candidate(o, path, repo, current_skill, "hard", "interrupt", "", last_assistant))
                continue
            if CMD_RE.search(txt):
                continue
            if HUMAN_PROMPT_SOURCES is not None and o.get("promptSource") not in HUMAN_PROMPT_SOURCES:
                continue
            if not seen_assistant:
                continue  # the first prompt of a session has nothing to correct
            if pending:
                for idx in pending:
                    found[idx]["after"] = flatten(txt, PROMPT_CHARS)
                pending = []
            found.append(candidate(o, path, repo, current_skill, "soft", "prompt",
                                   flatten(txt, PROMPT_CHARS), last_assistant))
    return found


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codepage
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=None, help="days back")
    ap.add_argument("--repo", default=None, help="filter to one repo")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--kind", choices=["hard", "soft", "all"], default="all")
    ap.add_argument("--limit", type=int, default=800, help="max candidates in the output")
    ap.add_argument("--commit-state", action="store_true",
                    help="record the end of this run in the state file (otherwise a dry run)")
    args = ap.parse_args()

    state = {}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            state = {}

    now = datetime.now(timezone.utc)
    if args.since is not None:
        since, window = now - timedelta(days=args.since), f"last {args.since} days"
    elif state.get("last_run"):
        since, window = parse_ts(state["last_run"]), f"since last run ({state['last_run'][:16]})"
    else:
        since, window = now - timedelta(days=30), "last 30 days (no state file)"

    if not os.path.isdir(PROJECTS):
        print(f"SKIP: transcript folder not found: {PROJECTS} (set FRICTION_PROJECTS_DIR)")
        return
    cands, sessions = [], 0
    for d in sorted(os.listdir(PROJECTS)):
        full = os.path.join(PROJECTS, d)
        if not os.path.isdir(full):
            continue
        repo = repo_name(d)
        if args.repo and repo != args.repo:
            continue
        for path in glob.glob(os.path.join(full, "*.jsonl")):
            if since and datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < since:
                continue
            sessions += 1
            cands.extend(scan_file(path, repo, since))

    # dedup: the same stop is recorded both as an interrupt and as a denial
    seen, deduped = set(), []
    for c in cands:
        if c["kind"] == "hard":
            key = (c["session"], c["ts"][:16])
            if key in seen:
                continue
            seen.add(key)
        deduped.append(c)
    cands = [c for c in deduped if args.kind == "all" or c["kind"] == args.kind]
    cands.sort(key=lambda c: c["ts"])
    total = len(cands)
    limit = max(1, args.limit)
    dropped = max(0, total - limit)
    cands = cands[-limit:] if dropped else cands

    if args.format == "json":
        json.dump({"window": window, "sessions": sessions, "total": total, "dropped": dropped,
                   "candidates": cands}, sys.stdout, ensure_ascii=False, indent=1)
    else:
        hard = [c for c in cands if c["kind"] == "hard"]
        print(f"Window: {window} | sessions: {sessions} | candidates: {total}")
        print(f"Hard signals: {len(hard)} | soft: {total - len(hard)}")
        if dropped:
            print(f"DROPPED by --limit: {dropped} oldest candidates")
        print("")
        for c in cands:
            print(f"- {c['ts'][:16]} [{c['repo']}] {c['signal']} | skill: {c['skill']} | {c['prompt'] or '(no prompt)'}")
            if c["context"]:
                print(f"    agent before: {c['context']}")
            if c.get("after"):
                print(f"    human after: {c['after']}")

    if args.commit_state:
        state["last_run"] = now.isoformat()
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
