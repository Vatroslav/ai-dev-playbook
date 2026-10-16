---
name: setup-linting
description: Detects the project stack, installs a linter and formatter, and wires a format-on-save hook so every file the agent writes is formatted immediately. Use on "/setup-linting", "add linting", "set up prettier/eslint/ruff", "format on save", or when called by the setup skill. NOT for fixing individual lint errors in existing code.
argument-hint: "[optional: force-reinstall]"
---

# Setup linting

Why: an agent that writes unformatted code produces noisy diffs, and reviewers waste attention on whitespace. A hook that formats the one file just written keeps every commit clean without anyone remembering to run a formatter.

All config files are real files in `templates/` next to this skill; the hook script is the playbook's shared `hooks/format-on-save.sh` (`../../hooks/format-on-save.sh` relative to this file). Copy them; never rewrite them from memory. Why: a config retyped from memory drifts (wrong option names, old syntax) and nobody notices until CI.

## Preflight

- Not a git repo: print `SKIP: not a git repository` and stop.
- No source files at all (only Markdown, YAML, docs): print `SKIP: no code to lint` and stop.
- The playbook's `hooks/format-on-save.sh` is not reachable: print `SKIP: hook script not found - copy hooks/format-on-save.sh from the playbook first` and stop.

## Step 1: Detect the stack

| Indicator | Stack | Tools |
|---|---|---|
| `*.py` + (`pyproject.toml` or `requirements.txt`) | Python | ruff (lint + format) |
| `build.gradle.kts` + `*.kt` | Kotlin / Android | ktlint |
| `package.json` + `tsconfig.json` | TypeScript | ESLint 9 (flat config) + Prettier |
| `package.json` without `tsconfig.json` | JavaScript | ESLint 9 + Prettier |

Several stacks (for example a Python backend and a TS frontend): set up each one. Print what you detected and continue without asking.

## Step 2: Detect existing setup

Look for: `ruff.toml` or `[tool.ruff]` in `pyproject.toml`; the ktlint Gradle plugin; `eslint.config.{js,mjs,cjs,ts}` or `.eslintrc.*`; `.prettierrc*` or a `prettier` key in `package.json`; `.claude/scripts/format-on-save.sh`.

- **Framework-generated configs count as existing setup.** `create-next-app`, Vite and Expo templates ship their own ESLint config: never overwrite it or reinstall ESLint. Add only what is missing (usually Prettier, `eslint-config-prettier` and the hook).
- Everything present and no `force-reinstall`: print `Linting is already set up for this repo.` and stop.
- Partly present: add only what is missing; leave existing configs untouched.

## Step 3: Install and configure

**Python:** add `ruff` to the dev dependencies with the tool the repo already uses (`uv add --dev ruff`, `poetry add --group dev ruff`, or a line in `requirements-dev.txt`). Copy `templates/ruff.toml` to the root, or move its content under `[tool.ruff]` in `pyproject.toml` if that file already holds tool config.

**Kotlin:** add the block from `templates/ktlint.gradle.txt` to `build.gradle.kts` (root and each module). Check the current plugin version before pinning it. Copy `templates/.editorconfig` if the repo has none.

**JavaScript / TypeScript:** detect the package manager from the lockfile and use it for everything:

| Lockfile | Install | Run |
|---|---|---|
| `pnpm-lock.yaml` | `pnpm add -D` | `pnpm exec` |
| `yarn.lock` | `yarn add -D` | `yarn` |
| `bun.lockb` / `bun.lock` | `bun add -d` | `bunx` |
| `package-lock.json` or none | `npm install -D` | `npx` |

- Install `eslint @eslint/js prettier eslint-config-prettier`, plus `globals` for JavaScript or `typescript-eslint` for TypeScript.
- Copy `templates/eslint.config.javascript.mjs` or `templates/eslint.config.typescript.mjs` to the root as `eslint.config.mjs`. The `.mjs` extension works whether or not `package.json` has `"type": "module"`.
- Copy `templates/.prettierrc`. **Before the initial format, match it to the style the code already uses** (tabs or spaces, quote style, semicolons, line width). Why: the goal is consistency, not a rewrite of every line in the repo.
- Copy `templates/.prettierignore` if the repo has none.
- Add scripts to `package.json` only where the names are free: `"lint": "eslint ."`, `"format": "prettier --write ."`, `"format:check": "prettier --check ."`. CI calls these (see [CI and deploy](../../docs/agent/ci-cd-and-deploy.md)).

## Step 4: Wire the hook

1. Copy `../../hooks/format-on-save.sh` to `.claude/scripts/format-on-save.sh`. **Delete the `case` branches for stacks this repo doesn't use.** It formats only the file just written, only inside the repo, never downloads a tool, and always exits 0.
2. Make it executable for everyone: `chmod +x .claude/scripts/format-on-save.sh` and `git update-index --chmod=+x .claude/scripts/format-on-save.sh` after staging it. Why: without the git bit, teammates on macOS/Linux get a non-executable copy.
3. Merge the block from `templates/settings-hook.json` into the **committed** `.claude/settings.json`. Keep every existing setting; if a `PostToolUse` entry with matcher `Write|Edit` already exists, add the command to its `hooks` array instead of creating a second entry. Why: `settings.local.json` is personal and not shared, so a hook registered there protects only one machine.
4. Probe the hook before committing (pipe a fake tool call, check the file changed):

```bash
printf '{"tool_input":{"file_path":"%s"}}' "$(git rev-parse --show-toplevel)/path/to/some-file.ts" | bash .claude/scripts/format-on-save.sh; echo "exit=$?"
git diff --stat -- path/to/some-file.ts
```

Expected: `exit=0` and, if the file was unformatted, a diff. Revert that probe diff if you don't want it in the initial format commit.

## Step 5: Commit config, then the initial format separately

1. Commit the tooling with explicit paths: `git commit -m "chore: add linting and format-on-save hook" -- <config files> .claude/settings.json .claude/scripts/format-on-save.sh <package.json and lockfile if changed>`.
2. Run the initial format with the detected runner:
   - Python: `ruff format . && ruff check --fix .`
   - Kotlin: `./gradlew ktlintFormat`
   - JS/TS: `<run> prettier --write "**/*.{js,jsx,mjs,cjs,ts,tsx,json,css,scss,html,yaml,yml}" && <run> eslint --fix .`
3. If files changed, commit them alone: `style: apply initial formatting with <tool>`. Why: formatting in its own commit keeps that noise out of feature diffs (and `git blame` can skip it), and the `style:` type needs no version bump.
4. Lint errors that `--fix` can't fix: don't fix them here. List the count per rule in the report so the team can decide.

## What NOT to do

- Don't reformat Markdown. Docs are prose; reflowing them makes unreadable diffs. The hook skips `.md` on purpose.
- Don't touch files outside the repo. The hook checks this.
- The hook runs in Claude Code only (other agents edit files through tools whose input carries no file path). For everyone else, `format:check` in CI is the backstop.
- Don't let the hook block the agent: it must always exit 0, even when a formatter fails.
- Don't switch formatters a repo already uses (Black, Biome, dprint): wire the hook to the existing tool instead.

## Output

```
Linting setup
- Stack:     <detected stacks>
- Installed: <tools + versions>
- Configs:   <paths created / kept as-is>
- Hook:      .claude/scripts/format-on-save.sh, registered in .claude/settings.json (probe: ok)
- Commits:   <SHA chore: ...> <SHA style: ... | no formatting changes>
- Remaining lint errors: <rule: count, ... | none>
- Restart the agent session so the hook loads.
```

## force-reinstall

Skip the existing-setup check, reinstall the tools and overwrite the configs and the hook. Show the diff of every overwritten file in the report.
