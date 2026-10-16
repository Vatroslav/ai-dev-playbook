#!/usr/bin/env python3
"""Doc-drift gate: a staged change under a documented module must also stage its doc.

The most common doc drift is new behaviour added under a topic that is already
documented. This gate maps code paths to the doc(s) that describe them and fails
when code under a mapped path is staged without any of its docs.

Fill in DOC_MAP below, or keep the map in a JSON file and pass --map <file>
(same shape: {"path/prefix/": ["doc/a.md", "doc/b.md"]}). Any ONE listed doc
satisfies its prefix. Extend the map in the same PR that adds a module.

Exit codes: 0 = PASS (or SKIP when the map is empty / nothing staged), 1 = FAIL,
2 = git error (e.g. unknown --base ref).
On FAIL there are two honest exits: update the doc and re-run, or record an
explicit waiver ("waived: <doc> - <reason>", e.g. pure refactor) in the ledger.

Usage:
  doc_drift.py [--map docs/agent/doc-map.json] [--base origin/main]
  (without --base it checks the staged diff; with --base it checks base...HEAD)
"""
import argparse
import json
import subprocess
import sys

# path prefix -> docs that describe it (fill in per repo)
DOC_MAP = {
    # "src/billing/": ["docs/billing.md", "docs/architecture.md"],
    # "src/api/": ["docs/api.md"],
}


def changed_files(base):
    if base:
        cmd = ["git", "--no-pager", "diff", "--name-only", f"{base}...HEAD"]
    else:
        cmd = ["git", "--no-pager", "diff", "--staged", "--name-only"]
    out = subprocess.check_output(cmd).decode()
    return {line.strip() for line in out.splitlines() if line.strip()}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--map", help="JSON file with the prefix -> docs map")
    p.add_argument("--base", help="compare base...HEAD instead of the staged diff")
    args = p.parse_args()

    doc_map = DOC_MAP
    if args.map:
        with open(args.map, encoding="utf-8") as f:
            doc_map = json.load(f)
    if not doc_map:
        print("SKIP: doc map is empty - fill in DOC_MAP or pass --map")
        return 0

    try:
        changed = changed_files(args.base)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git diff failed (exit {e.returncode}) - check the --base ref")
        return 2
    if not changed:
        print("SKIP: nothing changed")
        return 0

    missing = []
    for prefix, docs in sorted(doc_map.items()):
        touched = [f for f in changed if f.startswith(prefix) and f not in docs]
        if touched and not any(d in changed for d in docs):
            missing.append(f"{prefix} changed ({len(touched)} file(s)) - expected one of: {', '.join(docs)}")

    if missing:
        print("FAIL: doc drift")
        for m in missing:
            print("  " + m)
        return 1
    print("PASS: every changed documented module has a doc change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
