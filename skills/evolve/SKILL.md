---
name: evolve
description: Structured review of accumulated agent feedback and the friction log - promotes recurring corrections into permanent rules (AGENTS.md, path-scoped rules, docs, skills) and prunes rules that no longer carry weight. Every change goes through human review, one proposal at a time. Run monthly or via /evolve. NOT for writing a brand-new skill - use /create-skill.
disable-model-invocation: true
---

# Evolve

Turns corrections into rules and removes dead rules, with a human deciding each change. Why: corrections that stay in personal memory or chat are lost to the team, and rules that are never pruned bury the ones that matter.

## Phase 0: Preflight

Inputs:
- Team feedback: `docs/agent/feedback/*.md` (committed).
- Personal feedback (optional, each developer runs on their own machine): Claude Code memory files `~/.claude/projects/*/memory/feedback_*.md` or equivalent. Map each memory folder to its repo; `--claude-worktrees-*` suffixes belong to the same repo.
- Friction log: `docs/agent/friction-log.md`, section "Recurring patterns".
- Current rules: `AGENTS.md`, `CLAUDE.md`, `.claude/rules/*.md`, nested `AGENTS.md` files, `docs/agent/*.md`, and skills that own protocols.
- Principles: `docs/agent/skill-principles.md`.

Checks:
1. No feedback files and no recurring patterns -> `SKIP: no feedback to review`, stop.
2. `AGENTS.md` unreadable -> `SKIP: AGENTS.md unavailable - can't judge coverage`, stop.
3. `docs/agent/evolution-log.md` missing -> create it with the header `# Evolution log` and the line "What /evolve accepted, rejected, archived or pruned: source, target, reason."
4. Freshness: take the last `## YYYY-MM-DD` in the evolution log; nothing modified since -> `SKIP: nothing new since last run (<date>)`.
OK -> `Preflight OK: N feedback files from M sources, P recurring patterns, last run <date>`.

## Phase 1: Scan

1. Read every feedback file: name, content, date, origin (repo or person-agnostic area). The same lesson from two people or two repos is a signal, not a duplicate. Skip files with `status: DECLINED`; report only "N previously declined, skipped".
2. Read all current rules listed in Preflight.
3. Classify each feedback item: **Covered** (an existing rule has the same intent) / **Partially covered** / **Unprocessed**. For friction patterns, also note whether a rule exists and is being broken.
4. Route each unprocessed item to the narrowest place that covers it:
   - A skill, if the lesson only matters inside one workflow.
   - A path-scoped rule or nested AGENTS.md, if it only matters for part of the tree.
   - A `docs/agent/*.md` topic doc (with a "Read BEFORE" pointer), if it matters for one kind of work.
   - `AGENTS.md`, only if it changes behaviour in most sessions.
   - When torn between team-wide and project-specific: project. A wrong global rule silently changes every session.
   - "Rule exists but is broken" -> propose a stronger mechanism (checklist in a skill, then hook, lint or CI), not another rule.

## Phase 2: Proposals (at most 5 per run)

Group by the **Principle:** line: items sharing a principle become ONE rule. Look first for an existing rule covering that principle. Items without a Principle line: propose one.

Priority:
1. A pattern from two or more sources -> one rule; archive all source files.
2. Feedback already fully covered -> archive it (delete the file, and its memory index line if it is personal memory).
3. Unprocessed feedback -> exact line(s) for the most natural file and section; merge into an existing section; new section only if none fits; one to three lines, each with "Why:".
4. Partially covered -> show what exists and what is missing.
5. Broken rule -> the enforcement step up.

Each proposal:
```
**Name:** <2-4 words>
**Type:** promote | archive | strengthen | enforce
**Source:** <feedback file(s) or friction pattern>
**Target:** <file, section>
**Change:** <exact text, as a diff>
**Reason:** <one sentence>
```

## Phase 3: Review

Show proposals one at a time: Accept / Modify / Reject.
- Accept -> apply now (edit the target; archive the source feedback).
- Modify -> ask what to change; re-offer.
- Reject -> no rule change; add `status: DECLINED` under `metadata:` in the feedback file; log the reason.

## Phase 4: Pruning (at most 3 per run)

Scope: only the rule files read in Phase 1. Not the tracker (that is `/janitor`), not memory.
Signals: rules for situations that no longer happen; sections whose tool, file or service is gone (verify it is gone before proposing); contradictions (propose which one stays); duplicates (propose the canonical place). Same review flow; delete only on Accept. None -> "No pruning candidates."

## Phase 5: Log and commit

Append to `docs/agent/evolution-log.md`:
```
## YYYY-MM-DD
- **Accepted|Rejected|Archived|Pruned**: <name> (<source> -> <target>). <reason if rejected>
```
Commit every changed file with explicit paths: `git commit -m "docs(agent): evolve - <short summary>" -- <paths>`, then follow the repo's PR workflow. If a skill changed, sync its `.agents/skills/` copy in the same commit.

## Rules

- Never change a rule file without review.
- Every proposal traces to a feedback file, a friction pattern, or a pruning signal. Never "might be useful".
- Rules are deleted only through Phase 4.
- At the end, say how many unprocessed items remain (one run rarely clears a backlog).
- Nothing to do -> "No unprocessed feedback. All up to date."
