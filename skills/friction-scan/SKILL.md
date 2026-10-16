---
name: friction-scan
description: Find where humans had to correct the agent - a script extracts candidates deterministically from your local Claude Code transcripts (interrupts, rejected tool calls, follow-up prompts), the agent classifies them and appends real friction to docs/agent/friction-log.md, and updates the recurring-patterns table. Monthly, before /evolve, or /friction-scan [days]. Never creates rules itself.
disable-model-invocation: true
argument-hint: "[days back, default: since last run]"
---

# Friction scan

Makes recurring agent mistakes visible from evidence instead of from whoever remembers to complain. Why: corrections that stay in chat are forgotten by the next session; a pattern only becomes fixable once it is counted.

Script: `python .claude/skills/friction-scan/scripts/friction_scan.py` (Codex: `.agents/skills/...`). It only extracts; it never classifies or writes the log.

## Preflight

- `docs/agent/friction-log.md` missing -> create it from the playbook's `templates/friction-log.md`.
- Transcripts live on each developer's machine; each teammate runs this on their own sessions. The script prints `SKIP: transcript folder not found` if there are none (set `FRICTION_PROJECTS_DIR` if your transcripts live elsewhere).
- If your repos are not in a folder called `projects`, set `FRICTION_REPOS_DIR` to that folder's name so repo names come out clean.

## Steps

1. **Extract:** `python .claude/skills/friction-scan/scripts/friction_scan.py --since <days> --repo <this repo>` (omit `--since` to continue from the last committed run; omit `--repo` to scan all your repos). If `--kind soft` returns nothing at all, check one transcript's `promptSource` field and set `FRICTION_PROMPT_SOURCES` (or `any`).
2. **Calibrate on hard signals first:** every `user-rejected` or `interrupt` candidate is near-certain friction; read the "human after" line to see what was wrong.
3. **Classify soft candidates:** most follow-up prompts are normal conversation. Real friction = the human corrected a claim, undid scope, repeated an instruction, or rejected the approach. Type each real one: `context`, `invented`, `scope`, `bug`, `copy`, `overload`, `omission`, `process` (definitions in the log header).
4. **Append** to `## Findings` in the log: `### YYYY-MM-DD - run N (sample: N candidates reviewed, M real)`, then one line per real item: `date | repo | skill | type | one-line summary`. **Summaries only: never quotes, user or customer names, data values or secrets.**
5. **Update `## Recurring patterns`:** increment counts; add a pattern when a type of mistake reaches three; set Status to `Rule missing` or `Rule exists - being broken` (check AGENTS.md, docs/agent and skills before choosing).
6. **Commit state** only after the log is written: `python .claude/skills/friction-scan/scripts/friction_scan.py --since 0 --commit-state` (scans nothing, records now as the start of the next window). Commit the log with an explicit path and the repo's PR flow.
7. **Report** in at most five lines: candidates, real friction by type, patterns that reached three, and "ready for /evolve" if any did.

## Boundaries

- Never writes or edits rules, skills or AGENTS.md; promotion goes through `/evolve` with a human yes per item.
- The log is for prioritization, not proof: classification is model-based and makes mistakes.
- Never copies transcript text into the repo.

## Headless mode

Runs unattended: extract, classify, append, update patterns, commit. Items you can't classify confidently are listed under the run heading as `unclear` with a one-line reason, not guessed.
