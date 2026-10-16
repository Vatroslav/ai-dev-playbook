<!--
Security reference for the team's agent setup. Copy to docs/agent/security-setup.md (or keep it in the shared agent-config repo).
Behavioural rules live in AGENTS.md and docs/agent/security.md; THIS file is the reference for WHAT is in place, WHERE, WHY, how to VERIFY it and how to ROLL IT BACK.
Write down the reason for every intentional block, so nobody re-approves it out of habit.
Update it in the same commit as any change to hooks, permissions, deny rules, CI security steps or secret handling.
-->

# Security setup

Last full review: YYYY-MM-DD by <@handle>

## Threat model

- **Prompt injection through tool output** (web pages, issues, emails, PDFs, logs, dependency READMEs) trying to make the agent:
  - read and exfiltrate a secret;
  - commit and push a secret;
  - push to an attacker-controlled remote;
  - enable a malicious MCP server or install a plugin.
- **Supply-chain attacks** (a compromised package or repo) that plant files which run automatically: a hook in a committed `.claude/settings.json`, a `.mcp.json`, a skill or plugin folder, a package `postinstall` script.
- **Accidents:** an agent deleting files outside git, force-pushing, running a production command, sweeping another session's files into a commit.
- <product-specific: e.g. cross-tenant data leak, personal data in logs or error reports>

## Measures

<!-- One section per measure. Keep "Verify" executable: an exact command and its expected output. -->

### 1. <name, e.g. Deny reading secrets>

- **Where:** <file and key, e.g. `.claude/settings.json` -> `permissions.deny`>
- **What:** <exact rule or behaviour>
- **Why:** <the threat or incident it addresses>
- **Limit:** <what it does NOT stop, e.g. "covers the Read tool only; shell access needs the guard in measure 2">
- **Verify:** `<exact pipe-test or command>` -> expected `<output / exit code>`
- **Rollback:** <exact steps to remove it, and who must approve>

### 2. <name>

- **Where:**
- **What:**
- **Why:**
- **Limit:**
- **Verify:**
- **Rollback:**

## Other guards (accident prevention, not injection defence)

| Guard | Where | Fires on | Verify |
|---|---|---|---|
| <e.g. explicit staging> | `.claude/hooks/<file>` | `git add -A`, path-less commit | `<pipe-test>` |

## Boundaries of the setup

<What bypasses what: plugins running inside the agent process, `disableAllHooks`, user-level vs project-level precedence (deny -> ask -> allow; a user-level deny beats a project allow), managed settings, CI vs local hooks.>

## Not done (conscious decisions)

| Not done | Why | Revisit when |
|---|---|---|
| <e.g. container isolation for agent sessions> | <friction vs current stakes> | <e.g. first paying customer / handling payments> |

## Maintenance

- A new hook ships only after a pipe-test on every OS the team uses (output AND exit code), plus a probe in the daily guard health check.
- After changing hooks, permissions or deny rules, pipe-test the change; if it doesn't seem to apply in a running session, restart the session.
- <list of machines / teammates whose user-level config must stay in sync>

## Secrets inventory

<!-- Names and locations only, NEVER values. -->
| Secret | Lives in | Scope | Rotate how | Last rotated |
|---|---|---|---|---|
| <name> | <secret manager / CI secret / local gitignored file> | <what it can do> | <steps> | YYYY-MM-DD |

Rotation order on suspected compromise: largest blast radius first.

## Change log

- **YYYY-MM-DD** - <cause> -> <change> -> verified: <command + measured result> -> rollback: <how>.
