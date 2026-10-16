#!/usr/bin/env python
"""todo_tool.py - deterministic helpers for docs/todo.md. Never parse dates or IDs by eye.

The tracker format is defined in the header of docs/todo.md (template: templates/todo.md):
an `## Active` table with 8 columns

    | ID | Status | Action | Prio | Owner | Trigger | Due | Depends |

Status: open | in-progress | blocked | done YYYY-MM-DD
Due:    YYYY-MM-DD, or YYYY-MM (= last day of that month), or "-" / empty
A postponed row carries "(moved from <D Mon>)" in its Action cell, once per postponement.
Details live under `## Details` as `### <ID> - title` blocks.

Commands (all read-only except `sweep`; none of them touch git state except `next-id --fetch`):
  next-id  [--prefix APP] [--no-fetch]   next free ID: max over the working file, the archive,
                                          and docs/todo.md + archive on every local and
                                          origin/* branch, plus one. IDs are never recycled.
  due      [--today YYYY-MM-DD]          open rows due today or overdue
  sunk     [--today ...] [--min-moves 3] open rows that are overdue AND postponed N+ times
  triggers                               open rows with a trigger (the weekly sweep checks them)
  check                                  table shape, unique IDs, valid Status and Due cells
  sweep    --older-than DAYS [--today ...] [--dry-run]
                                          move done rows (and their Details) older than DAYS
                                          into the archive; fail-closed integrity checks

Options: --file docs/todo.md  --archive docs/todo-archive.md
Exit codes: 0 ok, 1 usage/check failure, 2 integrity failure (nothing written).
"""
import argparse
import calendar
import re
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codepage
except (AttributeError, OSError):
    pass

COLS = 8
ROW_ID = re.compile(r"^\|\s*([A-Z][A-Z0-9]*)-(\d+)\s*\|")
DONE = re.compile(r"^done\s+(\d{4}-\d{2}-\d{2})$")
STATUSES = {"open", "in-progress", "blocked"}
EMPTY = {"", "-", chr(0x2014), chr(0x2013)}  # empty cell markers: nothing, hyphen, em dash, en dash
MOVED = re.compile(r"moved from", re.IGNORECASE)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_due(text):
    text = text.strip()
    if text in EMPTY:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", text)
    if not m:
        raise ValueError(f"bad Due value: {text!r}")
    y, mo, d = int(m.group(1)), int(m.group(2)), m.group(3)
    return date(y, mo, int(d) if d else calendar.monthrange(y, mo)[1])


def sections(lines):
    """Yield (section_name, index, line) for every line; section = text after '## '."""
    current = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            current = line[3:].strip()
        yield current, i, line


def active_rows(lines):
    rows = []
    for sec, i, line in sections(lines):
        if sec == "Active" and ROW_ID.match(line):
            rows.append((i, cells(line)))
    return rows


def is_open(status):
    return not status.lower().startswith("done")


def load(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"SKIP: {path} not found")
    return p.read_text(encoding="utf-8").splitlines()


def today_arg(a):
    return date.fromisoformat(a.today) if a.today else date.today()


# ---------- next-id ----------
def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")


def ids_in_text(text, prefix=None):
    out = []
    for line in text.splitlines():
        m = ROW_ID.match(line)
        if m and (prefix is None or m.group(1) == prefix):
            out.append((m.group(1), int(m.group(2))))
    return out


def cmd_next_id(a):
    found = []
    for path in (a.file, a.archive):
        p = Path(path)
        if p.exists():
            found += ids_in_text(p.read_text(encoding="utf-8"))
    sources = ["working tree"]
    inside = git("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    if inside:
        if not a.no_fetch:
            r = git("fetch", "--prune", "--quiet", "origin")
            if r.returncode:
                print(f"WARNING: git fetch failed, using local refs only: {r.stderr.strip()}", file=sys.stderr)
        refs = git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes/origin").stdout.split()
        refs = [r for r in refs if not r.endswith("/HEAD")]
        for ref in refs:
            for path in (a.file, a.archive):
                r = git("show", f"{ref}:{path}")
                if r.returncode == 0:
                    found += ids_in_text(r.stdout)
        sources.append(f"{len(refs)} branches")
    else:
        print("WARNING: not a git repo - scanned files only", file=sys.stderr)
    prefix = a.prefix
    if not prefix:
        if not found:
            sys.exit("No IDs found - pass --prefix (e.g. --prefix APP) for the first row.")
        prefix = Counter(p for p, _ in found).most_common(1)[0][0]
    nums = [n for p, n in found if p == prefix]
    nxt = (max(nums) if nums else 0) + 1
    print(f"{prefix}-{nxt:04d}")
    print(f"(max over {', '.join(sources)}; prefix {prefix})", file=sys.stderr)


# ---------- due / sunk / triggers ----------
def open_dated(lines, today):
    out = []
    for _, c in active_rows(lines):
        if len(c) != COLS or not is_open(c[1]):
            continue
        try:
            d = parse_due(c[6])
        except ValueError:
            print(f"WARNING: {c[0]}: unparseable Due {c[6]!r} - run `check`", file=sys.stderr)
            continue
        out.append((d, c))
    return out


def cmd_due(a):
    today = today_arg(a)
    rows = sorted((d, c) for d, c in open_dated(load(a.file), today) if d and d <= today)
    for d, c in rows:
        tag = "TODAY" if d == today else "OVERDUE"
        print(f"{tag:8} {d} {c[0]} [{c[4]}] {c[2]}")
    if not rows:
        print("Nothing due.")


def cmd_sunk(a):
    today = today_arg(a)
    rows = []
    for d, c in open_dated(load(a.file), today):
        moves = len(MOVED.findall(c[2]))
        if d and d < today and moves >= a.min_moves and c[5] in EMPTY:
            rows.append((-moves, d, c))
    for neg, d, c in sorted(rows):
        print(f"{c[0]} moved {-neg}x, due {d} [{c[4]}] {c[2]}")
    if not rows:
        print("Nothing has sunk.")


def cmd_triggers(a):
    rows = [c for _, c in active_rows(load(a.file))
            if len(c) == COLS and is_open(c[1]) and c[5] not in EMPTY
            and not c[5].lower().startswith("trigger met")]
    for c in rows:
        print(f"{c[0]} [{c[4]}] due={c[6] or '-'} trigger: {c[5]} | {c[2]}")
    if not rows:
        print("No open trigger rows.")


# ---------- check ----------
def cmd_check(a):
    lines = load(a.file)
    problems, seen = [], Counter()
    rows = active_rows(lines)
    for i, c in rows:
        rid = c[0]
        seen[rid] += 1
        if len(c) != COLS:
            problems.append(f"line {i + 1}: {rid} has {len(c)} cells, expected {COLS} (a '|' inside a cell?)")
            continue
        st = c[1]
        if st not in STATUSES and not DONE.match(st):
            problems.append(f"line {i + 1}: {rid} bad Status {st!r}")
        try:
            parse_due(c[6])
        except ValueError as e:
            problems.append(f"line {i + 1}: {rid} {e}")
    if Path(a.archive).exists():
        archived = {f"{p}-{n:04d}" for p, n in ids_in_text(Path(a.archive).read_text(encoding="utf-8"))}
        for rid in sorted(archived & {c[0] for _, c in rows}):
            problems.append(f"{rid} is both in Active and in the archive")
    for rid, n in seen.items():
        if n > 1:
            problems.append(f"{rid} appears {n} times in Active")
    if not rows:
        problems.append("no rows under '## Active'")
    for p in problems:
        print(f"PROBLEM: {p}")
    print(f"check: {len(rows)} active rows, {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


# ---------- sweep ----------
def details_block(lines, rid):
    """Return (start, end) of the '### <rid>' block under '## Details', or None."""
    start = None
    for sec, i, line in sections(lines):
        if start is None:
            if sec == "Details" and re.match(rf"^###\s+{re.escape(rid)}\b", line):
                start = i
        elif line.startswith("### ") or line.startswith("## "):
            return start, i
    return (start, len(lines)) if start is not None else None


def cmd_sweep(a):
    today = today_arg(a)
    cutoff = today - timedelta(days=a.older_than)
    lines = load(a.file)
    rows = active_rows(lines)
    header = None
    for sec, i, line in sections(lines):
        if sec == "Active" and line.startswith("| ID"):
            header = [line, lines[i + 1]]
            break
    swept = []
    for i, c in rows:
        m = DONE.match(c[1]) if len(c) == COLS else None
        if m and date.fromisoformat(m.group(1)) <= cutoff:
            swept.append((i, c))
    if not swept:
        print(f"Nothing to sweep (no done rows on or before {cutoff}).")
        return
    swept_ids = [c[0] for _, c in swept]
    drop = {i for i, _ in swept}
    moved_details = []
    for rid in swept_ids:
        blk = details_block(lines, rid)
        if blk:
            drop.update(range(*blk))
            moved_details.append("\n".join(lines[blk[0]:blk[1]]).rstrip())
    new_lines = [l for i, l in enumerate(lines) if i not in drop]

    arch = Path(a.archive)
    old_arch = arch.read_text(encoding="utf-8") if arch.exists() else "# TODO archive\nAppend-only. Rows swept from docs/todo.md; never edit or delete.\n"
    block = [f"\n## Swept {today} (done on or before {cutoff})", ""]
    block += (header or ["| ID | Status | Action | Prio | Owner | Trigger | Due | Depends |", "|---|---|---|---|---|---|---|---|"])
    block += [lines[i] for i, _ in swept]
    if moved_details:
        block += ["", "Details of the swept rows:", ""] + moved_details
    new_arch = old_arch.rstrip("\n") + "\n" + "\n".join(block) + "\n"

    # fail-closed integrity checks: better skip a sweep than corrupt the tracker
    before_open = {c[0] for _, c in rows if is_open(c[1])}
    after_rows = active_rows(new_lines)
    after_open = {c[0] for _, c in after_rows if is_open(c[1])}
    errors = []
    if not new_arch.startswith(old_arch.rstrip("\n")):
        errors.append("archive would not be append-only")
    if before_open != after_open:
        errors.append(f"open IDs changed: {sorted(before_open ^ after_open)}")
    if len(after_rows) != len(rows) - len(swept):
        errors.append(f"row count {len(rows)} - {len(swept)} != {len(after_rows)}")
    for rid in swept_ids:
        if not re.search(rf"^\|\s*{re.escape(rid)}\s*\|", new_arch, re.MULTILINE):
            errors.append(f"{rid} missing from archive")
        if details_block(new_lines, rid):
            errors.append(f"details of {rid} still in tracker")
    if errors:
        for e in errors:
            print(f"INTEGRITY: {e}")
        print("Nothing written.")
        sys.exit(2)
    print(f"Sweep: {len(swept)} row(s) -> {a.archive}: {', '.join(swept_ids)}")
    if a.dry_run:
        print("(dry run - nothing written)")
        return
    arch.write_text(new_arch, encoding="utf-8")
    Path(a.file).write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="docs/todo.md")
    ap.add_argument("--archive", default="docs/todo-archive.md")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next-id")
    p.add_argument("--prefix")
    p.add_argument("--no-fetch", action="store_true")
    for name in ("due", "sunk"):
        p = sub.add_parser(name)
        p.add_argument("--today")
        if name == "sunk":
            p.add_argument("--min-moves", type=int, default=3)
    sub.add_parser("triggers")
    sub.add_parser("check")
    p = sub.add_parser("sweep")
    p.add_argument("--older-than", type=int, required=True)
    p.add_argument("--today")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    {"next-id": cmd_next_id, "due": cmd_due, "sunk": cmd_sunk, "triggers": cmd_triggers,
     "check": cmd_check, "sweep": cmd_sweep}[a.cmd](a)


if __name__ == "__main__":
    main()
