#!/usr/bin/env python3
"""Verification ledger for the evidence-first workflow.

Every check the agent runs (build, tests, lint, smoke script, review) becomes one row.
The evidence bundle is printed from these rows, never written as prose.

The database lives in the OS temp directory (one file per repo), never in the repo.
Stdlib only. All values are bound as SQL parameters, so task ids, commands and
output snippets can contain any characters.

Usage:
  ledger.py init
  ledger.py add TASK PHASE CHECK --tool TOOL --cmd "COMMAND" --exit CODE [--passed 0|1] [--snippet TEXT]
  ledger.py show TASK
  ledger.py count TASK PHASE
  ledger.py regressions TASK
  ledger.py gate TASK --min-after N [--min-review M]
  ledger.py path

PHASE is one of: baseline, after, review.
--passed defaults to 1 when --exit is 0, else 0. Pass it explicitly for checks
where the exit code does not decide (e.g. a reviewer verdict, a waiver).
Override the database location with the LEDGER_DB environment variable.

The ledger idea comes from Burke Holland's Anvil agent (https://github.com/burkeholland/anvil);
this script is an independent implementation.
"""
import argparse
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

PHASES = ("baseline", "after", "review")
TASK_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SNIPPET_MAX = 300

SCHEMA = """
create table if not exists entries (
  id integer primary key autoincrement,
  task text not null,
  phase text not null check (phase in ('baseline','after','review')),
  name text not null,
  tool text not null,
  command text,
  exit_status integer,
  detail text,
  passed integer not null check (passed in (0,1)),
  recorded_at text default (datetime('now'))
);
"""


def ledger_path():
    if os.environ.get("LEDGER_DB"):
        return os.environ["LEDGER_DB"]
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        root = os.getcwd()
    digest = hashlib.sha256(root.encode()).hexdigest()[:8]
    return os.path.join(tempfile.gettempdir(), f"ledger-{digest}.db")


def connect():
    con = sqlite3.connect(ledger_path())
    con.executescript(SCHEMA)
    return con


def task_arg(value):
    if not TASK_RE.match(value):
        raise argparse.ArgumentTypeError("task id must be a slug: lowercase letters, digits, hyphens")
    return value


def print_table(cols, rows):
    rows = [["" if v is None else str(v).replace("\n", " ") for v in r] for r in rows]
    widths = [max([len(c)] + [len(r[i]) for r in rows]) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(v.ljust(widths[i]) for i, v in enumerate(r)))


def cmd_init(_args):
    connect().close()
    print(ledger_path())


def cmd_add(args):
    passed = args.passed if args.passed is not None else (1 if args.exit == 0 else 0)
    snippet = (args.snippet or "")[:SNIPPET_MAX]
    con = connect()
    with con:
        con.execute(
            "insert into entries (task, phase, name, tool, command, exit_status, detail, passed)"
            " values (?, ?, ?, ?, ?, ?, ?, ?)",
            (args.task, args.phase, args.check, args.tool, args.cmd, args.exit, snippet, passed),
        )
    con.close()
    print(f"recorded {args.phase}/{args.check}: {'PASS' if passed else 'FAIL'}")


def cmd_show(args):
    con = connect()
    cur = con.execute(
        "select phase, name, tool, command, exit_status, passed, detail"
        " from entries where task = ?"
        " order by case phase when 'baseline' then 0 when 'after' then 1 else 2 end, id",
        (args.task,),
    )
    rows = cur.fetchall()
    con.close()
    if not rows:
        print(f"no checks recorded for task '{args.task}'")
        return 1
    print_table(["phase", "check", "tool", "command", "exit", "passed", "detail"], rows)
    return 0


def count(con, task, phase):
    return con.execute(
        "select count(*) from entries where task = ? and phase = ?", (task, phase)
    ).fetchone()[0]


def cmd_count(args):
    con = connect()
    print(count(con, args.task, args.phase))
    con.close()


def regressions(con, task):
    # A regression: the latest baseline row for a check passed, the latest after row failed.
    return con.execute(
        """
        with latest as (
          select phase, name, passed
            ,row_number() over (partition by phase, name order by id desc) as rn
          from entries
          where task = ? and phase in ('baseline', 'after')
        )
        select b.name
        from latest b
        inner join latest a on a.name = b.name and a.phase = 'after' and a.rn = 1
        where b.phase = 'baseline' and b.rn = 1 and b.passed = 1 and a.passed = 0
        order by b.name
        """,
        (task,),
    ).fetchall()


def cmd_regressions(args):
    con = connect()
    rows = regressions(con, args.task)
    con.close()
    if not rows:
        print("None detected.")
        return 0
    for (name,) in rows:
        print(f"REGRESSION: {name} (passed in baseline, fails after)")
    return 1


def cmd_gate(args):
    con = connect()
    after = count(con, args.task, "after")
    review = count(con, args.task, "review")
    regs = regressions(con, args.task)
    con.close()
    problems = []
    if after < args.min_after:
        problems.append(f"after checks: {after} < {args.min_after}")
    if review < args.min_review:
        problems.append(f"review checks: {review} < {args.min_review}")
    if regs:
        problems.append("regressions: " + ", ".join(r[0] for r in regs))
    if problems:
        print("GATE FAIL: " + "; ".join(problems))
        return 1
    print(f"GATE PASS: after={after} review={review} regressions=0")
    return 0


def main():
    p = argparse.ArgumentParser(description="Verification ledger (evidence-first workflow)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("path").set_defaults(fn=lambda _a: print(ledger_path()))

    a = sub.add_parser("add")
    a.add_argument("task", type=task_arg)
    a.add_argument("phase", choices=PHASES)
    a.add_argument("check")
    a.add_argument("--tool", required=True)
    a.add_argument("--cmd", default="")
    a.add_argument("--exit", type=int, required=True)
    a.add_argument("--passed", type=int, choices=(0, 1))
    a.add_argument("--snippet", default="")
    a.set_defaults(fn=cmd_add)

    s = sub.add_parser("show")
    s.add_argument("task", type=task_arg)
    s.set_defaults(fn=cmd_show)

    c = sub.add_parser("count")
    c.add_argument("task", type=task_arg)
    c.add_argument("phase", choices=PHASES)
    c.set_defaults(fn=cmd_count)

    r = sub.add_parser("regressions")
    r.add_argument("task", type=task_arg)
    r.set_defaults(fn=cmd_regressions)

    g = sub.add_parser("gate")
    g.add_argument("task", type=task_arg)
    g.add_argument("--min-after", type=int, required=True)
    g.add_argument("--min-review", type=int, default=0)
    g.set_defaults(fn=cmd_gate)

    args = p.parse_args()
    rc = args.fn(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
