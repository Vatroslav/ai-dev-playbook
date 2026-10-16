"""Guard controller: checks that the guard hooks actually work, and reports anything new in your
repos that would load by itself (project hook, .mcp.json, skills-dir plugin).

Why: a hook that fails silently looks identical to a hook that lets the call through. Guards
die silently for boring reasons - a missing `jq`, `grep -P` unsupported in the locale, `python`
missing on another OS, a guard file that was never registered, an MCP tool that got renamed so
the matcher never fires again - and nothing in normal use shows it. This script fixes nothing and
blocks nothing; it only reports. Run it daily (scheduled task, CI on the config repo, or once a
day from a SessionStart wrapper).

Checks:
  1. registration - every guard-*.sh in ~/.claude/hooks/ is registered in settings; every
     registered hook has its file and (for PreToolUse) a probe in TESTS
  2. behaviour - each registered command (exactly as written in settings) gets probe payloads
     and must react as expected (deny/ask/block, or silent pass); plus test-guard-rm.sh
  3. matcher - if an MCP connector was used in the last 7 days but the exact tool name a guard
     waits for was never called, that guard never fires (the tool was renamed)
  4. repos - new project hooks, MCP servers or skills-dir plugins under REPOS_ROOT or
     ~/.claude/skills compared to the saved state; the first run only records the state
     (supply-chain worms plant exactly these files so they auto-run)

Environment: GUARD_REPOS_ROOT (folder that holds your clones, default ~/projects),
GUARD_CLAUDE_DIR (default ~/.claude).

Usage:
  python guard-controller.py                 text report
  python guard-controller.py --json          machine-readable
  python guard-controller.py --accept ID ... finding is known/intended, stop reporting it
Exit: 0 all good, 1 findings, 2 the check itself failed.
State: ~/.claude/guard-controller.json (machine state, do not sync it).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
CLAUDE = Path(os.environ.get("GUARD_CLAUDE_DIR") or HOME / ".claude")
HOOKS = CLAUDE / "hooks"
STATE = CLAUDE / "guard-controller.json"
REPOS_ROOT = Path(os.environ.get("GUARD_REPOS_ROOT") or HOME / "projects")
DAYS = 7  # how far back transcripts are read for tool names

# An existing file that is NOT under git (guard-paths must ask). Adjust if ~/.claude is a repo.
UNVERSIONED_PATH = (CLAUDE / "settings.json").as_posix()
MISSING_PATH = (HOME / "guard-controller-missing-file.txt").as_posix()
# Probes run with this cwd: it does not exist, so guard-rm cannot treat a probe target as a clean
# tracked file of whatever repo the controller happens to run in.
PROBE_CWD = (HOME / "guard-controller-no-such-dir").as_posix()

# Probe calls per guard: (tool, tool_input, expected). Expected: deny / ask / block (exit 2) /
# pass (empty output, exit 0). Add new probes at the END of a list so finding IDs stay stable.
# A new guard without an entry here is reported as "no-test".
TESTS = {
    "guard-secrets.sh": [
        ("Bash", {"command": "cat secrets/x.txt"}, "deny"),
        ("Bash", {"command": "ls -la"}, "pass"),
        ("Bash", {"command": "cat .env.local"}, "deny"),
        ("Bash", {"command": "cp .env.example .env"}, "pass"),
    ],
    "guard-git-remote.sh": [
        ("Bash", {"command": "git push https://example.com/x.git main"}, "deny"),
        ("Bash", {"command": "git push origin main"}, "pass"),
        ("Bash", {"command": "git remote add other https://example.com/x.git"}, "deny"),
    ],
    "guard-git-add-all.sh": [
        ("Bash", {"command": "git add -A"}, "deny"),
        ("Bash", {"command": "git add file.txt"}, "pass"),
        ("Bash", {"command": "git commit -m x"}, "deny"),
        ("Bash", {"command": "git commit -m x -- a.md"}, "pass"),
        ("Bash", {"command": 'git commit -m "a; b" -- a.md'}, "pass"),
        ("Bash", {"command": "git commit -m x -- a.md && git commit -m y"}, "deny"),
        ("Bash", {"command": "cat > notes.md <<'EOF'\ngit commit -m x\nEOF"}, "pass"),
        ("Bash", {"command": "bash <<'EOF'\ngit commit -m x\nEOF"}, "deny"),
    ],
    "guard-rm.sh": [
        ("Bash", {"command": "rm -rf build"}, "ask"),
        ("PowerShell", {"command": "Remove-Item -Recurse dist"}, "ask"),
        ("Bash", {"command": "rm tmp.py"}, "pass"),
    ],
    "guard-paths.sh": [
        ("Edit", {"file_path": UNVERSIONED_PATH}, "ask"),
        ("Write", {"file_path": MISSING_PATH}, "pass"),
    ],
    "check-delete-transaction.sh": [
        ("Bash", {"command": "psql -c 'DELETE FROM t WHERE id = 1'"}, "deny"),
        ("Bash", {"command": "psql -c 'SELECT 1'"}, "pass"),
    ],
}

LABEL = {"deny": "deny", "ask": "ask", "block": "block", "pass": "pass"}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    args = sys.argv[1:]
    state = load_state()
    if "--accept" in args:
        accepted = [a for a in args[args.index("--accept") + 1:] if not a.startswith("--")]
        state["accepted"] = sorted(set(state["accepted"]) | set(accepted))
        save_state(state)
        print("Accepted: " + ", ".join(accepted))
        return 0
    started = time.time()
    findings = []
    hooks = registered_hooks()
    findings += check_registration(hooks)
    findings += check_behaviour(hooks)
    findings += check_suite()
    findings += check_matchers(hooks)
    repo_findings, first_run = check_repos(state)
    findings += repo_findings
    shown = [f for f in findings if f["id"] not in state["accepted"]]
    state["last_check"] = time.strftime("%Y-%m-%d %H:%M")
    save_state(state)
    report = {
        "ok": not shown,
        "findings": shown,
        "accepted_count": len(findings) - len(shown),
        "first_run": first_run,
        "hook_scripts": len([h for h in hooks if h["script"]]),
        "time": state["last_check"],
        "duration_s": round(time.time() - started, 1),
    }
    if "--json" in args:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print_text(report)
    return 0 if report["ok"] else 1


# ---- 1. registration -------------------------------------------------------------------------

def registered_hooks():
    hooks = []
    for name in ("settings.json", "settings.local.json"):
        path = CLAUDE / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for event, blocks in (data.get("hooks") or {}).items():
            for block in blocks:
                for hook in block.get("hooks", []):
                    command = hook.get("command", "")
                    match = re.search(r"\.claude[\\/]hooks[\\/]([\w.-]+)", command)
                    hooks.append({
                        "event": event,
                        "matcher": block.get("matcher", ""),
                        "command": command,
                        "script": match.group(1) if match else None,
                    })
    return hooks


def check_registration(hooks):
    findings = []
    used = {h["script"] for h in hooks if h["script"]}
    for path in sorted(HOOKS.glob("guard-*.sh")):
        if path.name not in used:
            findings.append(finding("unregistered:" + path.name, "registration",
                                    f"{path.name} exists but is not registered in settings.json - it does nothing."))
    for hook in hooks:
        name = hook["script"]
        if not name:
            continue
        if not (HOOKS / name).exists():
            findings.append(finding("missing-file:" + name, "registration",
                                    f"{name} is registered but the file is missing - the hook fails on every call."))
        elif hook["event"] == "PreToolUse" and name not in TESTS:
            findings.append(finding("no-test:" + name, "registration",
                                    f"{name} has no probe in guard-controller.py - nobody knows if it works."))
    return findings


# ---- 2. behaviour ----------------------------------------------------------------------------

def check_behaviour(hooks):
    findings = []
    bash = find_bash()
    if bash is None:
        return [finding("no-bash", "behaviour", "bash not found - guards can neither run nor be checked.")]
    for hook in hooks:
        name = hook["script"]
        if hook["event"] != "PreToolUse" or name not in TESTS or not (HOOKS / name).exists():
            continue
        for n, (tool, tool_input, want) in enumerate(TESTS[name], 1):
            tool = tool or first_tool(hook["matcher"])
            payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "hook_event_name": "PreToolUse",
                                  "cwd": PROBE_CWD})
            got = run_hook(bash, hook["command"], payload)
            if got != want:
                shown = tool_input.get("command") or tool_input.get("file_path") or "probe"
                findings.append(finding(f"broken:{name}:{n}", "behaviour",
                                        f"{name} is broken: for '{shown}' it should {LABEL[want]}, but got {LABEL.get(got, got)}."))
    return findings


def run_hook(bash, command, payload):
    env = dict(os.environ)
    env.setdefault("HOME", HOME.as_posix())  # `~` in the registered command
    try:
        run = subprocess.run([bash, "-c", command], input=payload, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=30, env=env)
    except subprocess.TimeoutExpired:
        return "did not finish in 30 s"
    if run.returncode == 2:
        return "block"
    decision = None
    for line in run.stdout.splitlines():
        try:
            decision = json.loads(line).get("hookSpecificOutput", {}).get("permissionDecision") or decision
        except (ValueError, AttributeError):
            pass
    if decision:
        return decision
    if run.returncode == 0 and not run.stdout.strip():
        return "pass"
    return f"exit {run.returncode}"


def check_suite():
    suite = HOOKS / "test-guard-rm.sh"
    bash = find_bash()
    if not suite.exists() or bash is None:
        return []
    env = dict(os.environ)
    env.setdefault("HOME", HOME.as_posix())
    try:
        run = subprocess.run([bash, suite.as_posix()], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return [finding("suite:test-guard-rm", "behaviour", "test-guard-rm.sh did not finish in 5 minutes.")]
    lines = run.stdout.splitlines()
    failed = [line for line in lines if line.startswith("FAIL")]
    total = failed + [line for line in lines if line.startswith("ok ")]
    if failed or run.returncode != 0:
        example = failed[0][:100] if failed else "exit " + str(run.returncode)
        return [finding("suite:test-guard-rm", "behaviour",
                        f"test-guard-rm.sh: {len(failed)} of {len(total)} cases fail (e.g. {example}).")]
    return []


def find_bash():
    if os.name != "nt":
        return shutil.which("bash")
    # On Windows a bare `bash` from PATH may be WSL, not Git Bash - find Git Bash explicitly.
    candidates = [os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")]
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parent
        candidates += [root.parent / "bin" / "bash.exe", root.parent.parent / "bin" / "bash.exe"]
    candidates.append(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def first_tool(matcher):
    return re.split(r"[|,]", matcher)[0].strip() or "Bash"


# ---- 3. matcher ------------------------------------------------------------------------------

def check_matchers(hooks):
    seen = seen_tools()
    findings = []
    for hook in hooks:
        if hook["event"] != "PreToolUse":
            continue
        for wanted in mcp_names(hook["matcher"]):
            server = wanted.split("__")[1]
            same_server = sorted(t for t in seen if t.split("__")[1:2] == [server])
            if wanted in seen or not same_server:
                continue  # tool was used, or the connector was not used so we cannot tell
            tail = wanted.split("__", 2)[-1]
            similar = [t for t in same_server if t.split("__", 2)[-1] in tail or tail in t.split("__", 2)[-1]]
            hint = ", ".join(t.split("__", 2)[-1] for t in (similar or same_server)[:3])
            findings.append(finding("matcher:" + wanted, "matcher",
                                    f"{hook['script'] or hook['command'][:60]} waits for tool '{tail}', which was not "
                                    f"called in the last {DAYS} days - the same connector was used for: {hint}. "
                                    f"The guard never fires."))
    return findings


def mcp_names(matcher):
    # A matcher made only of letters, digits, _, -, spaces, | and , is compared as exact names.
    if not re.fullmatch(r"[A-Za-z0-9_\-\s|,]*", matcher or ""):
        return []
    return [part.strip() for part in re.split(r"[|,]", matcher) if part.strip().startswith("mcp__")]


def seen_tools():
    cutoff = time.time() - DAYS * 86400
    names = set()
    root = CLAUDE / "projects"
    if not root.exists():
        return names
    for path in root.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            with open(path, encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if '"tool_use"' in line:
                        names.update(re.findall(r'"name":"(mcp__[^"]+)"', line))
        except OSError:
            continue
    return names


# ---- 4. repos --------------------------------------------------------------------------------

def check_repos(state):
    current = {}
    roots = [p for p in sorted(REPOS_ROOT.glob("*")) if (p / ".git").exists()]
    for repo in roots:
        current.update(repo_items(repo, repo.name))
    current.update(skills_dir_plugins(CLAUDE / "skills", "~/.claude/skills"))
    first_run = state.get("known") is None
    if first_run:
        state["known"] = sorted(current)
        return [], True
    known = set(state["known"])
    new = [finding(key, "repo", text) for key, text in sorted(current.items()) if key not in known]
    return new, False


def repo_items(repo, label):
    items = {}
    for name in ("settings.json", "settings.local.json"):
        path = repo / ".claude" / name
        data = read_json(path)
        if data is None:
            if path.exists():
                items[f"hook:{label}:{name}:unreadable"] = f"{label}: .claude/{name} cannot be parsed."
            continue
        for event, blocks in (data.get("hooks") or {}).items():
            for block in blocks:
                for hook in block.get("hooks", []):
                    command = hook.get("command") or hook.get("url") or hook.get("prompt") or ""
                    items[f"hook:{label}:{event}:{digest(command)}"] = (
                        f"{label}: new {event} hook in .claude/{name}: {command[:90]}")
    mcp = repo / ".mcp.json"
    data = read_json(mcp)
    if data is None and mcp.exists():
        items[f"mcp:{label}:unreadable"] = f"{label}: .mcp.json cannot be parsed."
    for server, config in ((data or {}).get("mcpServers") or {}).items():
        items[f"mcp:{label}:{server}:{digest(json.dumps(config, sort_keys=True))}"] = (
            f"{label}: new or changed MCP server '{server}' in .mcp.json.")
    items.update(skills_dir_plugins(repo / ".claude" / "skills", label))
    return items


def skills_dir_plugins(skills, label):
    items = {}
    if not skills.exists():
        return items
    for manifest in sorted(skills.glob("*/.claude-plugin/plugin.json")):
        skill = manifest.parent.parent.name
        items[f"plugin:{label}:{skill}:{digest(manifest.read_bytes().decode('utf-8', 'replace'))}"] = (
            f"{label}: skill '{skill}' is a plugin (.claude-plugin) - it loads without installation.")
    return items


# ---- helpers ---------------------------------------------------------------------------------

def finding(key, kind, text):
    return {"id": key, "kind": kind, "text": text}


def digest(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def load_state():
    state = read_json(STATE) or {}
    state.setdefault("accepted", [])
    state.setdefault("known", None)
    return state


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def print_text(report):
    print(f"Guard controller {report['time']} ({report['duration_s']} s, hook scripts: {report['hook_scripts']})")
    if report["first_run"]:
        print("First run: current repo items recorded as known.")
    for item in report["findings"]:
        print(f"- [{item['id']}] {item['text']}")
    if report["ok"]:
        print("All good.")
    if report["accepted_count"]:
        print(f"(accepted findings not shown: {report['accepted_count']})")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # a check that crashes must never look like "all good"
        if "--json" in sys.argv:
            print(json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"}, ensure_ascii=False))
        else:
            print(f"Check failed: {type(error).__name__}: {error}")
        sys.exit(2)
