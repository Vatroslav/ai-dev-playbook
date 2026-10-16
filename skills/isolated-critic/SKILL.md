---
name: isolated-critic
description: Isolated critic - a fresh subagent scores an artifact (UI screenshot, landing or store copy, cover image, onboarding text, email draft, release note) 1-10 without seeing the conversation, brief or code, and returns its top objections plus "would you stop/click". A shared step other skills call in their critique phase; also "/isolated-critic <path or text>", "get a fresh pair of eyes on this", "critique this before we ship". NOT for code review - use the reviewer agents in agents/ for diffs.
argument-hint: "[artifact path or text] [optional: audience, direction constraints]"
---

# Isolated critic

The author always defends their work. A fresh reader doesn't know what was hard or what was intended, so it sees what the audience sees. That is why the critic is a separate subagent with a fresh context, never the session that made the artifact.

**Isolate from the implementation, not from the intent.** The critic must not see code, the brief, notes, source data or the conversation, but it MUST get the direction constraints. Why: critics without them keep pushing toward the same generic solution and tear down the direction the team already chose.

## Inputs

Required (print `SKIP: missing <input>` and stop if one is absent and can't be derived):
- **Artifact:** a path to a PNG/JPG/HTML/text file, or the text itself. Nothing else: a screenshot critic never sees the code; a copy critic never sees the source material or the earlier draft.
- **What it is and for whom, in one sentence:** e.g. "store screenshot #1 for a habit-tracking app, seen by someone scrolling search results on a phone".
- **Direction constraints, 2-3 sentences:** the chosen concept, structure, length, hard rules the author cannot change.

Optional (defaults in brackets):
- **Role** ["strict reader from that audience" for text, "strict art director" for visuals]. It judges; it never rewrites.
- **Not under review:** e.g. figures that come from the database, fixed legal text. Objections about these are ignored.
- **Threshold** [8]. **Max rounds** [2].
- **Display condition:** e.g. "readable at 210 px wide", "read on a phone in sunlight".
- **Output tweak:** a caller may replace the stop/click question or the number of objections. The 1-10 score and the no-rewrite rule always stay.

## Run

One fresh subagent per round (Agent/Task tool in Claude Code; a new session or `codex exec` run elsewhere). The prompt contains ONLY the inputs:

```
You are <role>. In front of you is <what it is and for whom>: <artifact or path>.
Direction constraints the author cannot change: <constraints>.
<Display condition, if any.> Do not assess <not under review, if any>.
Return exactly:
1. Score 1-10 (10 = no objection, I would publish it now).
2. Would you stop / click: yes or no, one sentence why.
3. The three biggest objections, by severity, one line each: what is wrong and what you would change.
4. One thing you would cut without loss.
Do not rewrite the artifact and do not write your own version.
```

## Loop

1. Score >= threshold: done.
2. Below the threshold: fix the objections that stay **within the direction**, then start a **new** critic. Never continue the old one: it has seen the previous version and will grade the improvement, not the artifact.
3. After max rounds without reaching the threshold: stop and deliver the artifact as it is, with the open objections. The decision is the human's. Why: a fresh critic always finds something, so extra rounds cost tokens without guaranteeing convergence, and a high threshold makes that worse.

## Not applied

- Objections that break the direction: record them; that call belongs to the product owner.
- Objections about anything marked "not under review".
- Factually wrong objections: treat them as a readability signal (something made the reader believe it), not as a description of the artifact.

## Log

The caller decides where (for example `promo/store/iter/critique.md`). Per round: score, stop/click, the three objections, what was changed. Without a log the step can't be evaluated and isn't worth its cost.

## Headless

Runs unattended: no question is asked once the required inputs are present. When max rounds end below the threshold, return the artifact plus the objection list; never loop further.

## Output (to the caller or the human)

```
Critic: <score>/10 after <n> round(s) (threshold <t>)
Stop/click: <yes|no> - <reason>
Open objections:
1. <objection>
2. <objection>
3. <objection>
Rejected (breaks direction / out of scope): <list or "none">
Log: <path>
```

## Callers

Callers pass only their specifics (artifact, context sentence, constraints, display condition, log location). Threshold, rounds and loop rules live only here; never copy them into a caller. Current callers: `store-page` (cover and screenshots), `new-web-app` (landing copy, optional).
