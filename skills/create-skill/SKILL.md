---
name: create-skill
description: Create a new agent skill with the team, step by step - consistent format, naming and structure, tested on one real case before commit. Use for "make a skill for X", "turn this workflow into a skill", "we keep doing this by hand", /create-skill. NOT for promoting feedback into rules - use /evolve.
argument-hint: "[what the skill should do]"
---

# Create skill

Turns a repeated workflow into a skill that triggers on the right words, does one job, and states its boundaries. Why: ad-hoc skills overlap, trigger unpredictably and accumulate rules nobody can trace.

## Preflight

- No description of the workflow in the argument or the conversation -> ask for one sentence: "What should the skill do, and what would you type to start it?" Then continue.
- `docs/agent/skill-principles.md` missing -> print `SKIP: docs/agent/skill-principles.md not found - copy it from the playbook first` and stop.

## Steps

1. **Look before writing.**
   - List existing skills: `.claude/skills/*/SKILL.md` (and `.agents/skills/*/SKILL.md` if the team uses Codex). Read two or three similar ones for format and naming.
   - Read `docs/agent/skill-principles.md` and apply it to every step you design.
   - If an existing skill already covers most of this, propose extending it instead. A near-duplicate triggers unpredictably.
   - Measure first when the skill exists to prevent a problem: how often did it actually happen (transcripts, friction log, tracker)? A rule existing is not evidence of frequency.
2. **Name it** with the word the team already types for this workflow (kebab-case, same as the folder). If no word is evident, ask which word they would type. Don't offer invented names. Avoid names of built-in commands and of personal skills (a personal skill overrides a project skill with the same name).
3. **Agree the steps with the user before creating files.**
   - Propose the steps (purpose, preflight, numbered steps, boundaries, output, headless mode if it may run unattended).
   - If the user has their own steps, compare and merge.
   - Every rule in the steps names its source (a failure, a decision, a feedback file). No source, leave it out.
   - Iterate until the user says the steps are right.
4. **Write `.claude/skills/<name>/SKILL.md`:**
   ```yaml
   ---
   name: <name>
   description: <what it does>. Use when <phrases people actually say>. NOT for <X> - use /<y>.
   argument-hint: "[args]"                 # optional
   disable-model-invocation: true          # only if it has side effects or only a human should start it
   ---
   ```
   Body sections, as applicable: Purpose (with why) / Preflight (`SKIP: <reason>`) / Step 0 state detection (if resumable) / Steps / Boundaries (what it never does) / Output (exact format; chat vs file) / Headless mode / Failure modes.
   - Workflow and routing stay in SKILL.md; tables, templates, examples and first-time setup go into sibling files it references.
   - Deterministic work (parsing, counting, date math, moving rows, IDs) goes into a script in `scripts/`; run the script once before committing.
   - For a user-only skill used from Codex, add `agents/openai.yaml` with `policy:` / `allow_implicit_invocation: false`.
5. **Test on one real case.** Run the skill as written, in a fresh session if possible. Fix every step where you had to guess. If it will run on a schedule, run it once headless as well.
6. **Sync and commit.** Copy the folder to `.agents/skills/<name>/` if the team uses Codex. Commit both paths explicitly: `git add .claude/skills/<name> .agents/skills/<name>` then `git commit -m "chore(skills): add <name>" -- .claude/skills/<name> .agents/skills/<name>` and open a PR following the repo's git workflow.

## Boundaries

- Never creates files before the user agreed the steps.
- Never adds rules without a source.
- Never edits other skills in the same change unless the user asked (overlaps are reported, not fixed silently).

## Output

```
Skill: /<name> - <one-line purpose>
Triggers on: "<phrase>", "<phrase>"
Files: .claude/skills/<name>/SKILL.md (+ <siblings>)
Tested on: <the real case> - <result>
PR: #<n>
```
