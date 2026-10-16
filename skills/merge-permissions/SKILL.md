---
name: merge-permissions
description: Consolidates the accumulated Claude Code permission allow list in the current repo - deletes dead exact-match one-offs, merges recurring read-only commands into prefix rules, wildcards an MCP server only when every one of its tools is read-only, keeps write commands narrow. Shows before and after and waits for a yes. Changes permissions, so only a human starts it - /merge-permissions.
disable-model-invocation: true
---

# Merge permissions

**Why entries pile up:** clicking "allow" stores the exact command string. An exact entry covers only that literal; any variant (another path, branch or PR number) asks again, and commands prefixed with a full `git -C "<path>"` never match each other. Prefix rules match the start of the command and stop the repeat prompts. A long dead list hides the few entries that matter.

## Step 1: find the files

1. `.claude/settings.local.json` in the repo - the main accumulation point (usually gitignored, personal).
2. `.claude/settings.json` in the repo - committed and shared; change it only through the repo's PR flow.
3. `~/.claude/settings.json` - reference for de-duplication only. **Never change it here.**

Touch ONLY `permissions.allow`. `deny` and `ask` are never changed. Rules are evaluated deny, then ask, then allow; a user-level deny beats a project allow.

## Step 2: classify each allow entry

- **A. Dead one-off -> delete:** an exact command containing something that varies (paths, branch names, PR numbers, file lists, inline scripts, one-off `curl`). Safe when it is read-only and already covered by a general rule, or plainly one-off. If it is needed again, it will ask once.
- **B. Recurring -> merge into a prefix rule:** dev commands (`pnpm lint 2>&1` -> `Bash(pnpm lint:*)`), read-only git and gh (`git status`, `git log`, `git diff`, `git show`, `git fetch`, `git rev-parse`, `git ls-files`, `gh pr list`, `gh pr view`, `gh pr checks`, `gh run list`, `gh run view`). One rule per (tool, subcommand) pair.
- **C. MCP -> wildcard only if the server is 100% read-only:** list its tools and check the verbs. Any write tool (create, copy, update, delete, send, upload, insert, label, draft) -> no wildcard; keep the read-only tools listed explicitly. Unsure -> no wildcard.
- **D. Duplicate of a user-level entry -> delete from the project file.**
- **E. Write commands -> keep narrow:** `git add <file>` stays per file - **never `git add:*`**. `git push` stays exact - **never `git push:*`** (it would allow `--force`). MCP write tools stay explicit. Allowed as prefixes: non-destructive recurring git such as `git switch:*` and `git pull --ff-only:*`.

Rule of thumb: unsure whether something is read-only -> treat it as a write.

## Step 3: show before and after, and wait for "yes"

```
Allow entries: <before> -> <after>
Deleted one-offs: <n> | Merged into prefixes: <n> rules | MCP wildcards: <n> | Duplicates removed: <n>
Not wildcarded: <server> (has <write tool>)
Non-obvious decisions: <entry> -> <why>
```
Then the new `allow` list in full. Apply nothing until the human says yes.

## Step 4: apply

Rewrite only the `allow` array, grouped: MCP, skills, Bash read-only prefixes, write commands. A gitignored local file takes effect immediately; a committed file goes through the repo's PR flow. Tell the human to restart the session if prompts don't change.

## Hard rules (no "just this once")

- No MCP wildcard for a server with any write tool.
- No write command generalized to a prefix; never `git add:*` or `git push:*`.
- The user-level file is reference only; `deny` and `ask` are never touched.
- Unsure -> it's a write.
- Always before/after plus explicit confirmation.

For the reasoning behind the deny and ask rules, see `docs/agent/security.md`.
