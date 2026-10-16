# Skill principles

Purpose: the rules every skill (and every rule promoted from feedback) is held to, so skills stay small, trigger correctly and actually change behaviour.
Read when: creating or editing a skill (`/create-skill`), promoting or pruning rules (`/evolve`), or when a skill keeps misfiring. Deliberately not auto-loaded: a rule needed rarely must not cost context constantly.

Skills use the open Agent Skills format: a folder with a `SKILL.md` (YAML frontmatter with `name` and `description`, then instructions) plus optional sibling files. Claude Code reads `.claude/skills/<name>/`; Codex reads `.agents/skills/<name>/`. Keep one canonical copy and sync the other (copy or symlink) in the same commit.

## 1. Lean content

- **Every line of an always-loaded file costs context in every session.** A rule needed only inside one workflow goes into that workflow's skill, or into a doc the skill points to.
- **Before adding, check whether an existing section already covers it; merge before growing.**
- **If a rule doesn't change behaviour, delete it.**
- **Extend an existing skill before creating a near-duplicate.** Why: two skills with overlapping descriptions trigger unpredictably.

## 2. Built-in enforcement

- **A rule needs a mechanism that makes compliance likely, not just a description that hopes to be read.**
- **Strength, weak to strong: a line in the skill, then a preflight or pre-delivery checklist in the skill, then a deterministic hook, lint rule or CI check.**
- **When a rule keeps drifting despite its description, that is the signal for a stronger mechanism, not louder wording.** Details: [agent setup](agent-setup.md#2-rules-skills-and-hooks).

## 3. Traceability

- **Every rule ties to a concrete trigger: a feedback file, a decision, or a documented failure. No source, no rule.**
- **Each rule names the failure it prevents, in one line.** Why: without the reason, the agent "simplifies past" the rule and future editors delete it.
- **No rules based on "might be useful".**
- **Keep long incident history in a sibling file (`history.md`), not in SKILL.md;** keep the trail of promotions in the evolution log.

## 4. Progressive disclosure

- **SKILL.md is loaded in full whenever the skill triggers: keep it to the workflow and routing.**
- **Tables, templates, examples, long lists, first-time setup and troubleshooting go into sibling files** that SKILL.md references.
- **Test for each block: is it needed in EVERY run?** If not (only on error, only the first time, only for one step), it goes to a separate file with a pointer.

## 5. Design rules

### Triggering and naming

- **The description is the trigger.** The model decides from the description alone whether to load the skill. Write what it does, the phrases people actually say ("write this down", "what's next"), and "NOT for X - use /y" when a sibling exists. Put the main use case first: Claude Code truncates long descriptions in its skill listing.
- **For skills that prevent expensive mistakes, the description says to activate even when the task looks small.** Why: expensive errors often come in through tasks that look small.
- **Name the skill with the word the team already types for that workflow.** If no word is evident, ask which word they would type; don't offer lists of invented names. Why: a name nobody types is never invoked.
- **Skills with side effects, and user-only correctives ("your last answers were shallow"), must not auto-trigger.** Claude Code: `disable-model-invocation: true`. Codex: an `agents/openai.yaml` next to SKILL.md with:
  ```yaml
  policy:
    allow_implicit_invocation: false
  ```
- **A personal (user-level) skill overrides a project skill of the same name in Claude Code.** Avoid shared names; a generic skill checks for a project-local version first and defers to it.

### Structure of the body

- **Purpose, with the why, in one to three lines.**
- **Preflight: check required inputs and print `SKIP: <reason>` when one is missing.** Why: a skill that runs on missing inputs produces confident garbage.
- **Step 0 detects the current state, so the skill can be re-run and resumed** (which artifacts exist, which steps are done).
- **Numbered, concrete steps:** the command, the file, the tool.
- **A "Boundaries" or "What NOT to do" section:** the writes, sends, deletes, version bumps and pushes the skill never does.
- **An exact output format,** and what goes to chat versus to a file.
- **A headless mode when the skill can run unattended:** skip interactive steps, never ask, turn questions into lettered options in the output ("answer 1a 2c").
- **A failure-modes section with recovery steps a non-expert can follow** whenever the skill depends on something a human must refresh (a login, a token, a local service).
- **Record "facts not to rediscover" and "access boundaries"** (what the agent can and cannot reach). Why: it stops re-research of settled architecture and promises of checks the agent can't run.

### Behaviour

- **Detect everything you can; ask only what can't be derived. Propose rather than ask open questions** ("here are the five events I'd track" beats "what do you want to measure?").
- **The procedure lives in the skill; project specifics live in a config file per repo.** Never branch the skill on a project name; extend the config schema instead. Why: copies of a skill per project drift apart.
- **Templates are real files in the skill folder (`templates/`); copy them, never rewrite them from memory.** Why: rewritten templates mutate a little every time.
- **Deterministic work goes into a script in the skill folder** (parsing, counting, date math, moving rows, computing IDs). Judgment stays with the model. Why: the model misreads dates and counts; a script doesn't.
- **Setup skills are idempotent:** detect an existing setup and skip it, add only what is missing when partial, overwrite only on an explicit `force-reinstall`, never clobber framework-generated config, detect the package manager from the lockfile, and end with "restart the session" when hooks or permissions changed.
- **A shared step skill (for example the critic) owns its thresholds and loop rules; callers pass only their specifics.** Why: copied thresholds drift, and the loop rules end up different in every caller.
- **Read-only skills say so and name their single write exception, if any.** When the source doesn't say something (what's next, why a rule exists), they say it isn't written; they never invent it.
- **Writer skills do one thing** (add one item), grep headings instead of reading a large file, and chain the write into one approval (`git add <file> && git commit -m "..." -- <file> && git push`). Why: every separate command can raise its own permission prompt, and a chained write needs one approval instead of many.
- **An "it happened" skill (a release shipped, a meeting ended) is a checklist of every place to record it.** It never asks where to write.
- **Ops and deploy skills say "follow these steps exactly; do not improvise".**
- **Incremental-run state is written at the end, together with the delivery,** in a gitignored or clearly owned file. Why: a crashed run reprocesses instead of skipping silently.
- **Prompts inside skills that classify or extract are calibrated on 5-10 reference cases with known answers, and re-tested on every change.** Humans clean edge cases in the output; don't patch the prompt for each one. Why: a prompt patched for one edge case silently changes results on other cases, and without reference cases nobody notices.
- **When a skill needs randomness (seeded brainstorming, sampling), generate it with a script (`python -c "import secrets; print(secrets.token_hex(6))"`), not by the model "being random".** Why: a model choosing randomly picks what it likes.
- **Freshness fields (`verified`, `stale_after`) go under `metadata:` in SKILL.md.** Why: some skill uploaders reject unknown top-level keys; `metadata` is accepted everywhere.
- **When importing a skill written for another tool, add a table mapping its tool names to yours.**

## 6. Layout and frontmatter

```
.claude/skills/<name>/          (Codex: .agents/skills/<name>/)
  SKILL.md                      workflow and routing only
  reference.md                  tables, long lists, examples
  templates/                    files the skill copies
  scripts/                      deterministic helpers
  agents/openai.yaml            optional, Codex invocation policy
```

```yaml
---
name: <kebab-name, same as the folder>
description: <what it does>. Use when <phrases people say>. NOT for <X> - use /<y>.
argument-hint: "[what to pass]"          # optional, Claude Code
disable-model-invocation: true           # optional, Claude Code: side effects or user-only
metadata:                                # optional, free-form
  owner: "@handle"
---
```

## 7. Before committing a skill

- [ ] The description would trigger on the phrases the team actually uses, and not on a sibling's phrases.
- [ ] Preflight with `SKIP:` messages; Step 0 detects state if the skill is resumable.
- [ ] Boundaries section lists what it never does.
- [ ] Every rule names its failure; no rule without a source.
- [ ] Deterministic parts are scripts, and the scripts were run once.
- [ ] Tested on one real case; tested once headless if it will be scheduled.
- [ ] The Codex copy (`.agents/skills/`) matches.
