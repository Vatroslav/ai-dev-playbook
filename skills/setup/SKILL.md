---
name: setup
description: One-time repo setup for agent work - runs setup-linting, then setup-versioning, skipping whatever is already in place. Use on "/setup", "set up this repo", "prepare the repo for agents", or right after creating a new repo. NOT for adding a single piece to an already configured repo - call setup-linting or setup-versioning directly.
disable-model-invocation: true
argument-hint: "[optional: force-reinstall]"
---

# Setup

Gives every repo the same baseline in one command: a formatter and linter that run on every file the agent writes, and an intent-based version guard on every commit. Why: rules written in instructions get skipped under pressure, hooks don't. Doing it on day one keeps formatting noise and unversioned behaviour changes out of the history.

## Preflight

- `git rev-parse --show-toplevel` fails: print `SKIP: not a git repository` and stop.
- `git status --porcelain` shows uncommitted changes in files the sub-skills touch (`.claude/settings.json`, `AGENTS.md`, `CLAUDE.md`, `package.json`, lint configs): list them and continue only after the human says so. Why: setup commits must not absorb a teammate's work in progress.
- On `main` in a repo that already has a remote: create a branch `chore/agent-setup` from a freshly fetched `origin/main` first (see [git workflow](../../docs/agent/git-workflow.md)). A brand-new repo with no remote may take the setup commits on `main`.

## Steps

1. Invoke the skill `setup-linting`, passing the argument through.
2. When it finishes (also when it printed "already set up"), invoke `setup-versioning` with the same argument.
3. Print the summary below.

Run them one after the other, never in parallel: both edit `.claude/settings.json`.

## Rule shared by both sub-skills

Hooks parse JSON with Python, never `jq`. Why: `jq` is missing on many machines (notably Windows with Git Bash), and a hook whose parser is missing silently does nothing while everyone believes the guard is on.

## force-reinstall

Passed through to every sub-skill: existing configs and hooks are overwritten. Use it to upgrade an outdated setup, then review the diff before committing.

## What NOT to do

- Don't push or open a PR from here. The sub-skills commit locally with explicit paths; the normal git workflow takes it from there.
- Don't add tools the detected stack doesn't need.

## Output

```
Setup summary
- Linting:    <tools installed | already set up | SKIP: reason>
- Versioning: <version file + current version | already set up | SKIP: reason>
- Commits:    <short SHA + subject per commit, or "none">
- Next: restart the agent session so the new hooks load.
```
