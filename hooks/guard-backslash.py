# -*- coding: utf-8 -*-
"""PreToolUse hook (Claude Code, Bash tool): deny a shell command that contains two consecutive
backslashes.

Why: in the Bash tool of at least one Claude Code setup (Windows, Git Bash, late 2026), two
consecutive backslashes arrived at the shell as one - inside single quotes, inside a quoted
heredoc and inside `python -c` alike. Single sequences (a backslash followed by n, b or t) passed
unchanged. So `echo 'a' + two backslashes + 'b'` printed one backslash, and a Python string
written with an escaped backslash reached the interpreter as a bare escape: a regex word
boundary turned into a backspace character, invisible in grep and in the source text. A written
rule against it did not hold: the same failure came back several times after the rule existed.

Check your own setup before installing: in the Bash tool, run printf with a string that has two
backslashes between two letters and pipe it to `od -c`. If od shows two backslash characters,
your setup keeps them and you don't need this guard.

Decision: deny towards the agent (not ask the human). The agent rewrites the command: one
backslash where one is meant, or the code goes into a file (file-edit tool) that is then run.
The PowerShell tool is not checked: the conversion was not observed there.
"""
import json
import sys

REASON = (
    "The command contains two consecutive backslashes. The Bash tool may turn them into one "
    "before the shell runs the command (also inside '...', a quoted heredoc and python -c), so "
    "the code would not get what you wrote. If you mean one backslash, write one. If you need "
    "two (a Python string, a regex, JSON), write the code to a file with the file-edit tool and "
    "run the file, use chr(92) in Python, or use forward slashes in paths."
)


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
    except ValueError:
        return
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if "\\\\" in command:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }}))


if __name__ == "__main__":
    main()
