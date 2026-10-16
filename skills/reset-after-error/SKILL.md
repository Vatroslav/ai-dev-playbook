---
name: reset-after-error
description: Hard reset after the agent messed up - invented facts instead of reading the repo, answered without loading the relevant files, wrote information to memory or the wrong file. Names the error once, loads the real context, re-answers with every claim backed, and moves misplaced records. User-invoked - /reset-after-error, "you made that up", "you didn't read the file".
disable-model-invocation: true
argument-hint: "[optional: what went wrong or what should happen]"
---

# Reset after error

The human triggered this because you did one of these:
1. **Hallucinated** - invented data, facts, paths or APIs instead of reading the available context.
2. **Answered without reading** the relevant files, tracker or docs.
3. **Wrote to memory instead of the repo**, or **filed information in the wrong place**.

Why a hard reset: apologizing and patching the last answer keeps building on the same wrong foundation. Going back to the sources is cheaper than a second correction.

## Step 1: name the error

State exactly what was wrong, once: no excuses, no apology loop. For a hallucination, list each invented or incorrect claim.

## Step 2: load the context

- Read the project section of `AGENTS.md` and its sources-of-truth table; then every relevant file in full (task files, specs, `docs/decisions*.md`, `docs/todo.md`, the code involved), not just headings or grep snippets.
- No such docs -> the source code, README and recent git history of the involved paths.
- If the topic needs outside facts (library behaviour, API limits), check the official docs or the web before answering.

## Step 3: fix

- **Hallucination or no context:** answer the original question again from scratch. Every claim is backed by a file (`path:line`), a command output or a source URL. What is still unknown is said to be unknown.
- **Wrong memory write:** move the content to the right repo file (per the where-to-write-what table), delete the memory entry, update the memory index.
- **Wrong place:** remove it from the wrong file and add it to the right one, in one commit.

## Step 4: confirm

Say what you fixed and where the content lives now. Commit and open a PR if repo files changed. Then give the full, corrected answer, not "I've read it now". Acknowledge once and move on.

If the same kind of error happened before, offer to record a feedback file (Why / How to apply / Principle) so `/evolve` can turn it into a rule.
