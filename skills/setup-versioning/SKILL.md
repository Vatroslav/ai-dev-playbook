---
name: setup-versioning
description: Installs the intent-based version-bump guard (a Claude Code PreToolUse hook that blocks feat/fix/perf/breaking commits without a version bump, and source commits without a conventional type) plus a short Versioning section in AGENTS.md. Use on "/setup-versioning", "add the version guard", "set up versioning", or when called by the setup skill. NOT for bumping a version or cutting a release.
argument-hint: "[optional: force-reinstall]"
---

# Setup versioning

Why: without a guard, behaviour changes ship under the same version number, and nobody can tell which build a bug report is about. The guard ties the bump to the declared intent of the commit (its conventional type), not to which files changed, so a refactor never forces a bump and a feature never slips through without one.

The model itself (feat -> minor, fix/perf -> patch, breaking -> major, docs/chore/refactor/style/test/ci/build/revert -> no bump, tag only what reaches users) lives in ONE place: [docs/agent/versioning.md](../../docs/agent/versioning.md). Don't copy the rules into this skill or into the repo's AGENTS.md; the repo keeps only its deltas.

The hook script is `hooks/check-version-bump.sh` in this playbook (`../../hooks/check-version-bump.sh` relative to this file). Copy it from there; never retype it.

## Preflight

- Not a git repo: print `SKIP: not a git repository` and stop.
- The playbook's `hooks/check-version-bump.sh` is not reachable: print `SKIP: hook script not found - copy hooks/check-version-bump.sh from the playbook first` and stop.
- No working Python (`python`, `python3` or `py` that runs `-c 'import sys'`): print `SKIP: the hook needs Python to parse its input` and stop. The hook fails closed without Python, which would block every source commit.
- A prototype that may be thrown away: ask once whether to skip the guard until it proves it will live on. Default: install.

## Step 1: Find the version file

| Indicator | Version file | Version line |
|---|---|---|
| `package.json` in the root (Node, React, React Native, Vite, Next.js) | `package.json` | `"version": "1.2.3"` |
| `app/build.gradle.kts` | `app/build.gradle.kts` | `versionName = "1.2.3"` and `versionCode = N` |
| `pyproject.toml` with `[project] version` | `pyproject.toml` | `version = "1.2.3"` |
| A plain `VERSION` file (monorepos) | `VERSION` | `1.2.3` |

No version file: propose one (usually `package.json` or `VERSION`) with `0.1.0`, and create it after the human agrees. If the app shows its version somewhere (footer, settings, `/health`), note where: that copy must come from the version file at build time, never be typed by hand.

## Step 2: Detect existing setup

Check for `.claude/hooks/check-version-bump.sh`, its registration in `.claude/settings.json`, and a `## Versioning` section in AGENTS.md (or CLAUDE.md).
- All present and no `force-reinstall`: print `Versioning is already set up for this repo.` and stop.
- Partly present: add only what is missing.
- An older hook that decides by file path instead of commit type is outdated: replace it.

## Step 3: Install and configure the hook

1. Copy `../../hooks/check-version-bump.sh` to `.claude/hooks/check-version-bump.sh`.
2. Fill in the per-repo configuration block at the top of the script (`VB_SOURCE_RE`, `VB_VERSION_FILE`, `VB_VERSION_LINE_RE`; Python regex syntax, paths relative to the repo root):

| Stack | `VB_SOURCE_RE` (paths that ship to users) | `VB_VERSION_FILE` | `VB_VERSION_LINE_RE` (an added diff line = bump) |
|---|---|---|---|
| Node / Vite / React / Next.js | `^(src\|app\|lib\|components\|server)/` | `package.json` | `^\+\s*"version"\s*:` |
| Vanilla web app with source in the root | `^[^/]+\.(js\|css\|html\|webmanifest)$` | `package.json` | `^\+\s*"version"\s*:` |
| Android (Kotlin DSL) | `^app/\|^build\.gradle` | `app/build.gradle.kts` | `^\+\s*versionName` |
| Python package | `^(src\|app)/` | `pyproject.toml` | `^\+version\s*=` |
| Monorepo with a `VERSION` file | `^(web/src\|server/src\|packages/[^/]+/src)/` | `VERSION` | `^\+v?\d` |

   Adjust the source paths to the real layout (`ls`, don't guess). Data files the code imports count as source.
3. Make it executable: `chmod +x .claude/hooks/check-version-bump.sh`, and after staging `git update-index --chmod=+x .claude/hooks/check-version-bump.sh`.

## Step 4: Register the hook in the committed settings

Merge into `.claude/settings.json` (committed, so every teammate's agent and every worktree gets the guard; `settings.local.json` is personal). If a `PreToolUse` entry with matcher `Bash` already exists, add this command to its `hooks` array instead of creating a second entry:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/check-version-bump.sh", "statusMessage": "Checking version bump..." }
        ]
      }
    ]
  }
}
```

## Step 5: Probe the guard in a scratch clone

Never test by making real commits. Pipe fake tool calls into the hook inside a throwaway clone with one staged source change:

```bash
SCRATCH=$(mktemp -d)/probe && git clone -q . "$SCRATCH" && cd "$SCRATCH"
echo "// probe" >> <a real source file>
git add <that file>
probe() { printf '{"tool_input":{"command":"%s"}}' "$1" | bash .claude/hooks/check-version-bump.sh; echo " <- $1"; }
probe 'git commit -m \"update stuff\"'      # expect: deny (no conventional type)
probe 'git commit -m \"feat: add x\"'       # expect: deny (feat without bump)
probe 'git commit -m \"refactor: tidy x\"'  # expect: empty output (allowed)
```

A deny prints JSON whose `permissionDecision` is `deny`, with the reason; an allowed commit prints nothing. If another guard blocks the probe itself because its text mentions a commit, put these lines in a script file in the scratch folder and run it with `bash`. Then bump the version line in the scratch clone, stage it, and check that `feat:` is now allowed. All four must behave as expected before you continue. Tell the human the scratch folder path; it lives in the system temp folder and can be deleted.

## Step 6: Versioning section in AGENTS.md

AGENTS.md is read by every agent (CLAUDE.md imports it). Add a short pointer section with the repo's deltas only:

```markdown
## Versioning
Intent-based model, full rules: docs/agent/versioning.md. Guard: .claude/hooks/check-version-bump.sh (Claude Code hook).
- Version file: `<path>`; shown in the app at `<where>`, injected at build time.
- Source that activates the guard: `<paths>`.
- Put the message in the commit command (`-m`, `-F <file>` or a heredoc). With `--amend` / `--no-edit` the guard only warns: check the bump yourself.
```

Add a bullet only for a real delta (a second copy of the version that must match, a special tag flow, Android `versionCode`). If the repo has no `docs/agent/versioning.md` yet, copy it from the playbook.

## Step 7: Commit

`git commit -m "chore: add intent-based version guard" -- .claude/hooks/check-version-bump.sh .claude/settings.json AGENTS.md <version file if created>`

## Boundaries

- Does not bump the version, tag or release.
- The hook covers commits the agent makes. Manual commits, other tools and server-side merges are covered only by the CI version check (`ci/scripts/check-version-bump.mjs` in `ci/workflows/ci.yml`, explained in [versioning](../../docs/agent/versioning.md)). If the repo's CI doesn't run it yet, say so in the report.
- The hook checks the repo in the session's working directory: a `git -C other-repo commit` is checked against the wrong repo.

## Output

```
Versioning setup
- Version file:  <path> (current: <x.y.z>)
- Guard:         .claude/hooks/check-version-bump.sh, registered in .claude/settings.json
- Probe:         no-type deny / feat-without-bump deny / refactor allow / feat-with-bump allow: <ok | which failed>
- AGENTS.md:     Versioning section <added | already present>
- CI check:      <runs on PRs | missing: manual commits and merges are unguarded>
- Restart the agent session so the hook loads.
```

## force-reinstall

Overwrite the hook, its registration and the AGENTS.md section, including outdated path-based guards. Show the diff of every overwritten file.
