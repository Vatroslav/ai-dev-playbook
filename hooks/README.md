# Agent hooks

Purpose: working guard and workflow hooks for Claude Code (and the Bash guards for OpenAI Codex), with install, test and maintenance steps.
Read when: setting up a new machine or repo, adding or changing a hook, or when a guard seems not to fire.

Why these exist and what they defend against: [security guide](../docs/agent/security.md). Versioning model behind the version hooks: [versioning guide](../docs/agent/versioning.md). Commit and branch rules behind the git guards: [git workflow guide](../docs/agent/git-workflow.md).

## What is here

| File | Event / matcher | Level | Decision | What it does |
|---|---|---|---|---|
| `guard-rm.sh` + `guard-rm-reason.py` | PreToolUse `Bash\|PowerShell` | user | ask (Codex: block) | Asks before a delete that has no undo. Silent for temp files and for files tracked by git with no uncommitted changes. Catches `rm`, PowerShell `Remove-Item`/`del`/`rd`, `find -delete`, `xargs rm`, .NET `Delete()`, nested `bash -c`/`cmd /c`/`eval`, and Python/Node delete calls in inline code. |
| `guard-git-add-all.sh` | PreToolUse `Bash\|PowerShell` | user | deny | Blocks `git add -A/./--all` and any `git commit` without explicit paths (`git commit -m "..." -- path1 path2`). |
| `guard-secrets.sh` | PreToolUse `Bash\|PowerShell` | user | deny | Blocks shell commands that touch a `secrets/` path or read a real env file (`.env`, `.env.local`, `.env.production`...). `.env.example` stays readable. |
| `guard-git-remote.sh` | PreToolUse `Bash\|PowerShell` | user | deny | Pushes only to remotes that already exist: blocks `git remote add/set-url`, `git config remote.*.url`, and `git push <url>`. |
| `check-delete-transaction.sh` | PreToolUse `Bash\|PowerShell` | user | deny / ask | In commands that call a SQL client: `DELETE FROM` without `BEGIN` is denied, `DROP`/`TRUNCATE` asks. |
| `guard-paths.sh` | PreToolUse `Write\|Edit` | user | ask | Asks before overwriting an existing file that is not in any git repo (no undo). Silent for new files, repos and temp. Claude only. |
| `check-version-bump.sh` | PreToolUse `Bash\|PowerShell` | project | deny / warn | Intent-based version guard on `git commit`: source in the commit needs a conventional type; `feat`/`fix`/`perf`/breaking need the version line bumped in the same commit. Edit the config block at the top. |
| `check-version-decrease.sh` | PreToolUse `Write\|Edit` | project | deny | Blocks an edit that lowers the version in `package.json`, `VERSION`, `pyproject.toml`, `build.gradle(.kts)`, `app.json`. Edit `RULES`. Claude only. |
| `format-on-save.sh` | PostToolUse `Write\|Edit` | project | never blocks | Formats only the file just written, only if it is inside the repo, with the repo's own prettier/eslint/ruff/ktlint. Claude only. |
| `sync-main.sh` | SessionStart | project | never blocks | Fast-forwards the main checkout to `origin/main`; switches off a merged, clean branch; leaves dirty trees, unmerged branches and linked worktrees alone. |
| `freshness-check.py` | SessionStart | user | never blocks | Lists docs whose `stale_after` passed or whose body changed after the last `verified` entry (see [verification guide](../docs/agent/verification.md)). Needs PyYAML. |
| `guard-controller.py` | scheduled, daily | user | report only | Health check: every guard registered, every registered guard answers its probes, MCP matchers still match real tool names, and new project hooks / `.mcp.json` servers / skill plugins in your clones are reported. |
| `claude-settings.user.example.json` | | user | | `~/.claude/settings.json`: permissions (deny/ask/allow) and wiring for the user-level hooks. |
| `claude-settings.project.example.json` | | project | | `<repo>/.claude/settings.json`: wiring for the project hooks. |
| `codex-hooks.example.json` | | user | | `~/.codex/hooks.json`: the Bash guards for Codex. |
| `test-guard-rm.sh`, `test-hooks.py`, `test-guard-controller.py` | | | | Test suites (see "Testing"). |
| `../githooks/pre-commit` | git pre-commit | repo or machine | blocks commit | gitleaks scan of staged changes. |

"User" hooks protect a person's machine across every repo; "project" hooks encode one repo's workflow and are shared through git.

## Install for Claude Code

Requirements: bash (Git Bash on Windows), git, Python 3 (`python` or `python3`), PyYAML for `freshness-check.py` (`pip install pyyaml`), gitleaks for the pre-commit hook.

User level (each teammate, once per machine):

```bash
cd <this-playbook>
mkdir -p ~/.claude/hooks
cp hooks/guard-*.sh hooks/guard-rm-reason.py hooks/check-delete-transaction.sh \
   hooks/freshness-check.py hooks/guard-controller.py hooks/test-guard-rm.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh
```

Then merge `claude-settings.user.example.json` into `~/.claude/settings.json` by hand (keep your existing keys; JSON has no comments, so read the reasoning in [security guide](../docs/agent/security.md#permissions-model)). Hooks live in `~/.claude/hooks/`, outside every repo the agent edits freely: code that runs by itself must sit where a change needs a human. The ask rules in the example cover `~/.claude/settings.json` and `~/.claude/hooks/**` for the same reason.

Project level (once per repo, committed):

```bash
cd <your-repo>
mkdir -p .claude/hooks .claude/scripts
cp <this-playbook>/hooks/check-version-bump.sh <this-playbook>/hooks/check-version-decrease.sh .claude/hooks/
cp <this-playbook>/hooks/format-on-save.sh <this-playbook>/hooks/sync-main.sh .claude/scripts/
git update-index --add --chmod=+x .claude/hooks/*.sh .claude/scripts/*.sh   # exec bit survives Windows checkouts
```

Convention: guards (can deny) in `.claude/hooks/`, helpers that never block in `.claude/scripts/`. The `setup-versioning` and `setup-linting` skills install the same files to the same places.

Copy `claude-settings.project.example.json` to `.claude/settings.json` (committed, so every teammate and every cloud session gets it), not `settings.local.json` (personal, not shared). Edit the config block in `check-version-bump.sh` and `RULES` in `check-version-decrease.sh`; delete the formatter branches your stack does not use. Protect `.claude/`, `.codex/` and `githooks/` with CODEOWNERS so a change to self-running code needs a review.

After install:
- Settings edits are normally picked up by the file watcher. If a hook does not fire, restart the session, then pipe-test it (below).
- `/hooks` in Claude Code shows the configured hooks (read-only).
- Run `python ~/.claude/hooks/guard-controller.py` once: the first run records the current state of your clones (set `GUARD_REPOS_ROOT` to the folder that holds them) and must end with "All good." With the user settings example and the scripts above installed, it registers 7 hook scripts and every probe passes.

## Install for Codex

```bash
mkdir -p ~/.codex/hooks
cp hooks/guard-*.sh hooks/guard-rm-reason.py hooks/check-delete-transaction.sh hooks/freshness-check.py ~/.codex/hooks/
cp hooks/codex-hooks.example.json ~/.codex/hooks.json    # or merge into an existing file
```

Then open Codex and review/trust the hooks with `/hooks`. Non-managed hooks do not run until trusted, and trust is tied to the hook definition, so a changed definition must be trusted again. Facts that shape the Codex setup:
- Codex reads hooks from `~/.codex/hooks.json`, `<repo>/.codex/hooks.json` (only when the project `.codex/` layer is trusted) or `[hooks]` in `config.toml`.
- The shell tool is matched as `Bash`; stdin JSON carries `tool_name`, `tool_input.command` and `cwd`, the same fields the guards read.
- `permissionDecision: "deny"` and exit code 2 with the reason on stderr both block.
- `permissionDecision: "ask"` is parsed but not supported: the hook run is marked failed and the tool call proceeds. That is why `guard-rm.sh` and `check-delete-transaction.sh` run with `--codex`, which turns "ask" into a block (exit 2). The human runs those commands, or approves them through Codex's own approval mode.
- File edits go through `apply_patch`, whose input has no `file_path`, so `guard-paths.sh`, `check-version-decrease.sh` and `format-on-save.sh` do not apply.
- A project-level `.codex/hooks.json` can reuse the repo's Claude hooks: `"command": "bash \"$(git rev-parse --show-toplevel)/.claude/hooks/check-version-bump.sh\""`.
- Windows: which shell runs `command` is not documented. `commandWindows` overrides the command on Windows; point it at Git Bash explicitly (`bash` on a Windows PATH may be WSL) and confirm with a probe that a guard really blocks. A hook that crashes or prints invalid JSON lets the call through, so an unverified Windows install is no protection.

## Install the pre-commit secret scan

Per repo, shared by the team (recommended; each teammate runs it once after cloning, or a `prepare` script in `package.json` runs it):

```bash
cd <your-repo>
mkdir -p githooks && cp <this-playbook>/githooks/pre-commit githooks/
git update-index --add --chmod=+x githooks/pre-commit
git config core.hooksPath githooks
```

Per machine, every repo:

```bash
mkdir -p ~/.config/git/hooks && cp githooks/pre-commit ~/.config/git/hooks/ && chmod +x ~/.config/git/hooks/pre-commit
git config --global core.hooksPath ~/.config/git/hooks
```

Warnings:
- A global `core.hooksPath` makes git ignore every repo's `.git/hooks/`. The script chains the repo's own `.git/hooks/pre-commit` at the end, but other hook types (commit-msg, pre-push) in `.git/hooks/` stop running.
- A repo-local `core.hooksPath` (husky sets one) overrides the global one, so the global scan silently does not run there. Add `gitleaks git --staged --redact` to that repo's own pre-commit.
- Local hooks can be skipped. Keep GitHub secret scanning with push protection on as the server-side layer (see [security guide](../docs/agent/security.md#secrets)).
- Check it works: stage a fake key that is not on the gitleaks allowlist and commit; the commit must be blocked.

## Pipe-testing a hook

A hook is a program that reads one JSON object on stdin. Test it exactly that way, and check three things: stdout (decision JSON), stderr, exit code.

```bash
cd <this-playbook>
# build the trigger string from parts so YOUR running guards do not fire on this test command
p="secr""ets/token.txt"
printf '{"tool_name":"Bash","tool_input":{"command":"cat %s"}}' "$p" | bash hooks/guard-secrets.sh; echo "exit=$?"
# expected: {"hookSpecificOutput":{..."permissionDecision":"deny"...}}  exit=0

cmd="r""m -rf build"
python -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$cmd" \
  | bash hooks/guard-rm.sh --codex; echo "exit=$?"
# expected: reason on stderr, exit=2
```

Decisions: `deny`/`ask`/`allow` JSON on stdout with exit 0; exit 2 = block, stderr goes to the agent; any other non-zero exit = hook error, the call PROCEEDS (Claude shows a "hook error" notice; Codex marks the run failed). Empty stdout with exit 0 = pass.

Rules for tests:
- **Build destructive trigger strings from parts** (`"r""m -rf"`, `"secr""ets/"`), or generate them inside a test file. Why: the live guard in your own session fires on the test command, and the human sees an alarming prompt with no context and denies it.
- **An "ask" approved by the human looks the same to the agent as no prompt at all.** Only denies and blocks are visible to the agent, so end-to-end tests of ask-type hooks need a human watching.
- **Test every OS the team uses.** A hook that works on one machine can be dead on another (missing `python`, a `grep` without `-P`, CRLF line endings).

## Testing

| Suite | Covers | Run | Result on Windows / Git Bash |
|---|---|---|---|
| `test-guard-rm.sh` | guard-rm: false positives, temp targets, real deletes, .NET, nested shells, heredocs, Python/Node code, git-undo rule in a throwaway repo, Codex dialect, fallbacks | `bash hooks/test-guard-rm.sh` | 131 of 131 pass |
| `test-hooks.py` | every other hook: syntax, LF endings, JSON validity, pipe tests, throwaway repos for version bump, sync-main and freshness, fake formatter for format-on-save, gitleaks pre-commit | `python hooks/test-hooks.py` | 132 of 132 pass |
| `test-guard-controller.py` | the health check catches: unregistered guard, missing file, missing probe, broken guard, missing Python (guards fail closed, degradation reported), renamed MCP tool, new project hook / `.mcp.json` / skill plugin, broken settings | `python hooks/test-guard-controller.py` | 12 of 12 pass |

Not yet run on macOS or Linux; run all three there before relying on them. `test-hooks.py` and `test-guard-controller.py` need a scratch folder outside the system temp dir and outside any git repo (default: your home folder; override with `GUARD_TEST_BASE`). Run the suites in CI on the repo that holds these files.

## Keeping guards alive

A hook that fails silently looks exactly like a hook that lets the call through. Guards die for boring reasons: `jq` not installed, `grep -P` unsupported, `python` missing on another OS, a script never registered, an MCP tool renamed so an exact-name matcher never fires again.

- **Run `guard-controller.py` daily** (cron, Task Scheduler, or a scheduled agent run) and read the report. Exit 0 = all good, 1 = findings, 2 = the check itself failed. `--accept ID` silences a known, intended finding.
- **Every new guard gets a probe** in `TESTS` inside `guard-controller.py` (append, so finding IDs stay stable). A registered guard without one is reported.
- **Security guards fail closed, workflow hooks fail visibly.** Without a working Python the guards here scan the raw hook JSON (more prompts, never fewer); the version-bump guard denies commits; `check-version-decrease.sh` exits 1 so a "hook error" notice appears; `freshness-check.py` prints that PyYAML is missing.
- **Before shipping a change to a guard, replay real commands.** Extract a few thousand historical shell commands from your agent transcripts, run them through the old and new version and diff the decisions. Run the old version against the new tests as a control: it must fail them, which proves the tests catch the bug.
- **Remove a guard whose premise is gone** instead of keeping it alive, and do not build one on a premise that cannot hold: a flag file does not prove the agent read a document, because creating the file needs no reading.

## Writing a new hook

- Parse stdin with Python's `json`, never `jq` (often missing) or greedy `sed` (it also matches the `description` field and causes false denies). Interpreter: `PY=$(command -v python || command -v python3)`; where it matters, pick the first that actually runs (Windows has a `python3` stub that exists on PATH and fails).
- Write raw bytes to stdout from Python (`sys.stdout.buffer.write`): a text-mode `print()` on Windows turns `\n` into `\r\n`, and the trailing `\r` silently breaks path and string comparisons in bash.
- POSIX ERE only in `grep -E`: `[[:space:]]`, `(^|[^[:alnum:]_])` instead of `\b`; no `grep -P`.
- Exit 2 blocks and the agent reads stderr: write the reason there. For deny/ask JSON use stdout and exit 0.
- Put the exact trigger in the reason (the token, the line, the target). A human hunting through a long command for what fired starts approving blindly.
- Tie the guard to irreversibility, not location. Measure how often it will prompt per week before shipping; a guard that prompts on routine work gets switched off.
- Fail closed on ambiguity (a commit inside `bash -c "..."` is denied), with a blunt fallback when the smart parser crashes.
- A heredoc body consumed by an interpreter or tool (`python - <<'EOF'`, `git commit -F- <<'EOF'`) is data, not shell.
- Exact-name matchers (only letters, digits, `_`, `-`) compare whole tool names: a renamed MCP tool silently disables the guard. The guard controller checks this against recent transcripts.
- Store the file with LF endings (`.gitattributes` here does that) and the exec bit (`git update-index --chmod=+x`).
- Pipe-test it on every OS, add a probe to the guard controller, then call it active.

## Windows notes

- Claude Code runs hook commands through Git Bash when it is installed, otherwise PowerShell. Without Git Bash there is no `Bash` tool at all, so match `Bash|PowerShell`.
- From a subprocess (Python, Task Scheduler), call Git Bash by its full path: a bare `bash` may be WSL.
- `python3` on a fresh Windows is usually the Microsoft Store stub. The scripts try `python` first.
- CRLF line endings break bash scripts. Keep `* text eol=lf` for hook folders and check with `git ls-files --eol`.
- Set `PYTHONIOENCODING=utf-8` for Python inside hooks; the console code page cannot encode many characters and the hook then fails on a commit message with an accent.
- Git Bash rewrites `/flag` arguments of Windows programs into paths; run such tools from PowerShell or prefix `MSYS_NO_PATHCONV=1`.
- `cygpath -m` converts a Git Bash path (`/c/...`, `/tmp/...`) to one a native Windows program understands; `guard-rm.sh` does this for the session cwd.

## Environment variables

| Variable | Used by | Effect |
|---|---|---|
| `GUARD_RM_GIT_UNDO=0` | guard-rm | Turn off the "clean tracked file passes" rule (always ask). |
| `GUARD_RM_REASON_PY` | guard-rm | Path of the decision script (default: next to the hook). |
| `SYNC_MAIN_BRANCH`, `SYNC_MAIN_REMOTE` | sync-main | Default `main`, `origin`. |
| `GUARD_REPOS_ROOT` | guard-controller | Folder that holds your clones (default `~/projects`). |
| `GUARD_CLAUDE_DIR` | guard-controller | Agent config folder (default `~/.claude`). |
| `GUARD_TEST_BASE` | test suites | Scratch folder outside temp and outside git (default: home). |
| `GITLEAKS_BIN` | pre-commit | Absolute path to gitleaks when it is not on PATH yet. |

## Known limits

- Pattern guards parse command text; they are a speed bump, not a sandbox. Use a container or VM for a real boundary.
- `guard-git-add-all.sh` cannot stop two sessions editing the same file in one checkout; use separate worktrees.
- `check-version-bump.sh` reads the message from the command; a message produced by `$(script)` cannot be read and the commit is denied with a hint to use `-m`.
- Permission rules (allow/ask/deny) match command strings too and share the same limit.
