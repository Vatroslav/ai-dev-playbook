#!/usr/bin/env bash
# PreToolUse hook (matcher Write|Edit): versions only go up.
#
# A version decrease is almost always a merge accident, a stale copy pasted over a newer file,
# or a misread number - and a store/registry rejects it later, far from the cause.
# Compares the version in the file on disk with the version in the new content (Write: content,
# Edit: new_string). Pre-releases sort below their release (1.2.0-rc.1 < 1.2.0).
# Claude Code only: Codex edits through apply_patch, whose input has no file_path.
#
# Edit RULES below for your stack: (path regex, [version regexes, group 1 = the value]).
INPUT=$(cat)
PY=''
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then PY=$c; break; fi
done
if [ -z "$PY" ]; then
  # Visible, non-blocking: the call proceeds and a "hook error" notice shows the reason.
  echo "check-version-decrease: no working Python interpreter - guard inactive" >&2
  exit 1
fi

IFS= read -r -d '' VD_PY <<'PYEOF'
import json, re, sys

RULES = [
    (r"(^|[\\/])package\.json$", [r'"version"\s*:\s*"v?([^"]+)"']),
    (r"(^|[\\/])VERSION$", [r"^\s*v?(\d+\.\d+\.\d+\S*)"]),
    (r"(^|[\\/])pyproject\.toml$", [r'^version\s*=\s*"v?([^"]+)"']),
    (r"(^|[\\/])build\.gradle(\.kts)?$", [r'versionName\s*=?\s*"([^"]+)"', r"versionCode\s*=?\s*(\d+)"]),
    (r"(^|[\\/])app\.json$", [r'"version"\s*:\s*"v?([^"]+)"']),
]


def key(v):
    base, _, pre = v.partition("-")
    nums = [int(x) for x in re.findall(r"\d+", base)][:3]
    nums += [0] * (3 - len(nums))
    return (nums, 0 if pre else 1, [int(x) for x in re.findall(r"\d+", pre)])


data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
ti = data.get("tool_input") or {}
path = ti.get("file_path") or ""
if "new_string" in ti:
    new_texts = [ti.get("new_string") or ""]
elif "edits" in ti:
    new_texts = [e.get("new_string") or "" for e in ti.get("edits") or []]
else:
    new_texts = [ti.get("content") or ""]

for file_re, patterns in RULES:
    if not re.search(file_re, path):
        continue
    try:
        with open(path, encoding="utf-8") as fh:
            current = fh.read()
    except OSError:
        sys.exit(0)  # new file: nothing to compare
    for pat in patterns:
        cur = re.search(pat, current, re.M)
        if not cur:
            continue
        for text in new_texts:
            new = re.search(pat, text, re.M)
            if new and key(new.group(1)) < key(cur.group(1)):
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Version decrease blocked in {path}: {cur.group(1)} -> "
                                                f"{new.group(1)}. Versions only go up; if this is a merge "
                                                "or a stale copy, take the higher version."}}))
                sys.exit(0)
PYEOF

printf '%s' "$INPUT" | PYTHONIOENCODING=utf-8 "$PY" -c "$VD_PY"
exit 0
