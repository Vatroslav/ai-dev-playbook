# Review and research agents

Purpose: ready-made subagent definitions for reviewing diffs and researching dependencies, plus the rules that make their output trustworthy.
Read when: installing these agents, wiring a reviewer into a workflow, or deciding whether a review result can gate a merge.

## What is here

| Agent | Job | Default model | Writes | FAIL when |
|---|---|---|---|---|
| [code-reviewer](code-reviewer.md) | repo hard rules, duplicates, dead code, docs + bump in the same commit, consistency | sonnet | own memory folder only | any High finding |
| [security-reviewer](security-reviewer.md) | data access boundary, auth, injection, secrets, exfiltration into git, PII leaks | opus | own memory folder only | any Critical or High finding |
| [logic-reviewer](logic-reviewer.md) | off-by-one, wrong rules, edge cases, state transitions, with a triggering input | opus | nothing | any finding |
| [quality-reviewer](quality-reviewer.md) | long functions, magic values, duplication, names, tests that don't test, doc drift | sonnet | nothing | any finding |
| [research](research.md) | sourced research on a library, API or vendor, written to `docs/research/` | sonnet | `docs/research/` + own memory | (no verdict) |

Each file has a `<list here>` placeholder for project rules or invariants. Fill it in; a generic reviewer can't infer your repo's boundaries.

## Install

**Claude Code:** copy the files to `.claude/agents/` in the repo and commit them, so every teammate gets the same reviewers. Fields Claude Code doesn't recognise are ignored without an error, so after the first run check that a field like `memory` actually took effect (the folder `.claude/agent-memory/<name>/` appears).

Claude Code picks up edits to agent files automatically in recent versions. Restart the session after creating the first file in a new `.claude/agents/` folder, and whenever an edit doesn't seem to take effect (older versions read definitions only at session start).

**Codex and other agents:** the body of each file (everything below the frontmatter) is a self-contained review prompt. Run it as a separate, fresh review session (for example a non-interactive `codex exec` run) with the diff in scope, or register it as a custom agent if your Codex version supports that. Check your Codex version's docs for the current mechanism; don't assume a path.

## The verdict contract

- Every reviewer ends with exactly one last line: `VERDICT: PASS` or `VERDICT: FAIL`. Workflows and humans gate on that line, not on the tone of the text.
- **A missing verdict counts as FAIL.** It usually means the reviewer hit its turn cap (`maxTurns`) and returned partial output. Retry once and point it at the files it didn't get to; if it fails again, report it as unreviewed.
- Run independent reviewers in parallel, in one message. Spawn them by type and don't override their model in the call.
- Reviewers read `git diff --staged` by default: stage the change first, by explicit paths (never `git add -A`; another session's files would be reviewed and committed with yours).
- A FAIL is fixed, not argued with. If a finding is a false positive, say why in the PR and let the reviewer with memory record it, so it isn't raised again.

## Use a different model than the author

The reviewer must run on a different model from the session that wrote the code wherever possible. Why: same-model self-review is over-optimistic; it confirms what the author meant instead of what is there, while a different model finds real issues. Set `model:` per agent so at least the security and logic reviewers differ from the model the team usually codes with; for high-stakes changes, also run one review through a different vendor's agent. Both kinds of model share blind spots on concurrency and timezone math, so those still need a human pass.

## Verify the reviewer can actually read the repo

Before trusting a reviewer in a new environment (a sandbox, a cloud runner, another CLI), have it list the changed files and quote one changed line. Why: a reviewer that cannot list or read files may still report confidently, for example that files were deleted. The reviewers here are told to report unreadable files as unreviewed instead of guessing; still check. If you ever give a reviewer write access, run `git status` afterwards.

## Persistent memory for reviewers

`code-reviewer`, `security-reviewer` and `research` use `memory: project`: a folder `.claude/agent-memory/<name>/`, committed to git so the whole team's reviewers learn together.
- They read `MEMORY.md` before a review and record afterwards: critical code paths, recurring issues, where duplicates keep reappearing, and findings the team rejected as false positives.
- They may write only inside their own folder. Review that folder in PRs like any other file; delete notes that turned out wrong.

## When to run what

| Change | Reviewers |
|---|---|
| Any code change before commit | code-reviewer |
| Medium or large change (several files, new logic) | + logic-reviewer, quality-reviewer |
| Auth, data access, user data, payments, config, dependencies, `.gitignore` | + security-reviewer (mandatory) |
| High stakes (auth, payments, migrations, privacy) | + one review on a different vendor's model, + a human pass |
| Adopting a library or vendor | research (then decide; record it in `docs/decisions.md`) |

Built-in review commands of your agent tool are useful extra signals, but they don't replace this panel: the gate depends on the VERDICT line.

## Credits

`logic-reviewer`, `quality-reviewer` and `security-reviewer` are adapted from the "anvil" reviewer agents in [SenteLabsAI/OpenExecutive](https://github.com/SenteLabsAI/OpenExecutive/tree/69c0ae33eaeab05575a11eda7829bf7cc9ae3d08/.claude/agents) (Copyright 2025 Open Executive Contributors, [Apache License 2.0](../licenses/Apache-2.0.txt)). Each file carries a notice of its source and changes; those three files remain under Apache 2.0. See [NOTICE](../NOTICE.md).

## Related

- [Git workflow](../docs/agent/git-workflow.md): where review sits in the PR flow.
- [Security](../docs/agent/security.md): the rules the security reviewer enforces.
- [isolated-critic skill](../skills/isolated-critic/SKILL.md): the same fresh-eyes idea for non-code artifacts (copy, screenshots, covers).
