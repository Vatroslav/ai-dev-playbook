# AI Dev Playbook

A drop-in set of rules, skills, subagents, hooks, CI files and templates for a small team that builds software with AI coding agents (Claude Code, OpenAI Codex, or similar).

It is distilled from practices used in real production projects. Most rules come with a "Why" line, the failure it prevents. Agents follow rules with reasons noticeably better than bare commands, and humans can judge when a rule no longer applies.

## What's inside

| Path | What it is | Where it goes in your repo |
|---|---|---|
| `AGENTS.md` | Core rules every agent loads in every session. Short on purpose; it points to the docs below. | repo root |
| `CLAUDE.md` | One-line import of AGENTS.md plus Claude Code specifics. | repo root |
| `docs/agent/` | Topic guides the agent reads on demand (verification, git, testing, CI/CD, security, database, debugging, ...). | `docs/agent/` |
| `skills/` | About 45 skills in the open Agent Skills format (`SKILL.md` + helpers). | `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex) |
| `agents/` | Reviewer and research subagents. | `.claude/agents/` |
| `hooks/` | Guard and automation hooks with tests, plus example settings for Claude Code and Codex. | `.claude/hooks/` or `~/.claude/hooks/`; see `hooks/README.md` |
| `githooks/pre-commit` | gitleaks secret scan before every commit. | see `hooks/README.md` |
| `ci/` | GitHub Actions workflows, Dependabot config, PR template, version and docs-only check scripts with tests. | `.github/`, `scripts/`; see `ci/README.md` |
| `templates/` | Ready-to-copy files: todo tracker, task file, decision log, ADR, spec, design brief, readiness checklist, and more. | `docs/` |

## Quick start

1. Copy `AGENTS.md`, `CLAUDE.md` and `docs/agent/` into the root of your repo.
2. Fill in the **Project** section at the top of `AGENTS.md`: what the product is, the stack, commands, and the worst thing an agent could do there. Use `templates/project-section-skeleton.md`.
3. Copy the skills you want (start small, see below) into `.claude/skills/` and/or `.agents/skills/`.
4. Copy `templates/todo.md` to `docs/todo.md` and `templates/decisions-log.md` to `docs/decisions.md`.
5. Install the hooks and the pre-commit secret scan by following `hooks/README.md`, then the CI files by following `ci/README.md`.
6. Restart your agent session, then ask it: "Read AGENTS.md and summarize the rules you will follow in this repo." Correct anything it got wrong.

### Claude Code

- `CLAUDE.md` imports `AGENTS.md` with `@AGENTS.md`, so both tools share one rules file. Recent Claude Code versions also read a bare `AGENTS.md` when no `CLAUDE.md` exists; the import works in every version.
- Project skills: `.claude/skills/<name>/SKILL.md`. Subagents: `.claude/agents/<name>.md`.
- Register hooks in the committed `.claude/settings.json`, not in `settings.local.json`, so every teammate and worktree gets them.
- User-level config (`~/.claude/settings.json`, `~/.claude/hooks/`) is the place for the security guards that should protect every repo on a machine. See `hooks/claude-settings.user.example.json`.

### OpenAI Codex

- Codex reads `AGENTS.md` natively.
- Repo skills go in `.agents/skills/<name>/SKILL.md`, with the same format. The Claude-only frontmatter field `disable-model-invocation` has a Codex equivalent: an `agents/openai.yaml` next to `SKILL.md` with `policy: allow_implicit_invocation: false`.
- Hooks go in `.codex/hooks.json`; see `hooks/codex-hooks.example.json`. The same guard scripts work, because Codex sends the same stdin JSON and exit code 2 blocks the call. Codex does not support "ask" decisions yet, so guards that would ask in Claude Code either block or pass in Codex, as described in `hooks/README.md`.
- The `agents/` files can be used as review prompts. Check your Codex version's docs for custom agent support.

## Which skills to start with

Don't install them all on day one. Every skill description is loaded into context, and a skill nobody triggers is noise.

**Week one (most teams):**
- `evidence-first`: the main coding loop (size the task, baseline, implement, verify with real commands, evidence bundle).
- `feature-pr`: branch, commit, PR, merge, confirm what got deployed.
- `todo`, `next`: a lightweight task tracker in the repo.
- `setup`: installs linting, format-on-save and the version guard.
- `verify-claims`, `reset-after-error`: for when the agent says something you doubt.

**By area:**

| Area | Skills |
|---|---|
| Coding workflow | evidence-first, feature-pr, release, release-note, work-log, spec-format |
| Backend and data | backend-route-checklist, api-client, verify-without-infra, data-surface-gates, sqlite-migration, sql-runbook, sql-sync, data-sanity-check |
| Frontend and product | design-fidelity, copy-voice, new-web-app, store-page, telemetry, humanizer |
| Deploy | deploy-static, deploy-vps |
| Repo setup | setup, setup-linting, setup-versioning, merge-permissions |
| Review and quality | isolated-critic, verify-claims, strict-mode, reset-after-error |
| Planning and tracking | todo, next, tasks, note-this, decisions-mode, sink-test, janitor, validate-idea, thinking-partner |
| Improving the agent itself | create-skill, evolve, friction-scan, decision-capture, deep-context, explain-simpler |

## Adapting it

- **Cut what doesn't fit your stack.** The rules assume Git + GitHub, a web or mobile product, and a staging environment before production. If you have no staging yet, keep the rule that agents never touch production and hand prod commands to a human.
- **Keep AGENTS.md short.** Codex stops reading AGENTS.md files after 32 KiB combined by default, and long instruction files reduce adherence in every tool. Put new detail in `docs/agent/` or in a skill, and add a one-line pointer.
- **When a rule keeps getting broken, don't shout it louder.** Move it into a checklist inside a skill, or enforce it with a hook. `docs/agent/skill-principles.md` explains this escalation.
- **Record corrections.** When you correct the agent, write the lesson down with its Why (`templates/feedback-memory.md`). Periodically promote recurring lessons into AGENTS.md or a skill (`skills/evolve`).

## Caveats

- **Hooks and scripts run code on your machine. Read them before installing.** They were tested on Windows with Git Bash and Python 3; macOS/Linux should work (POSIX shell, `python` or `python3`) but test them yourself with the pipe tests in `hooks/README.md`.
- **Workflow files use placeholder action SHAs and provider-specific steps** that fail on purpose until you fill them in.
- **Tool features change fast.** Where a file makes a claim about Claude Code or Codex behaviour, check it against the current official docs before relying on it.

## License and credits

[MIT with the Commons Clause](LICENSE): you may use, copy, modify and share this playbook, including inside your company, but you may not sell it or a product or service whose value comes substantially from it. This makes it source-available, not open source in the OSI sense.

Some files are adapted from other projects and keep their own licences (the three reviewer agents are Apache 2.0); others build on credited ideas. See [NOTICE.md](NOTICE.md).
