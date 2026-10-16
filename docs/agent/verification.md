# Verification

Purpose: How the agent establishes that a claim is true before stating it, and what "done" has to mean before anyone reports it.
Read when: before reporting a task as done, stating anything about an external system, putting a number in a conclusion, recommending a tool or approach, or writing a fact into a repo file.

The core idea: anything the agent says is a proposal until a tool call, a live read or a human has confirmed it. Humans on the team will treat the agent's statements as facts, so an unchecked claim costs a correction and some trust every time it turns out wrong.

## External systems: check live

- **Check the live state of an external system before making a claim about it.** Use a read-only check: an API GET, `curl` on the live page, an `INFORMATION_SCHEMA` query, `gh api repos/OWNER/REPO/...`, a `--dry-run`. Repo notes, old tasks and handoffs are where you start looking, never the source of the claim. If you cannot check live, say so: "per the note from <date>, not verified live." Why: notes go stale silently, and the right answer is usually one read-only call away.
- **Fetch fresh before diagnosing.** Never reason from an old dump, a snapshot, a cached export or a `last_updated` field. Why: you end up debugging a state that no longer exists.
- **Take config values and thresholds from the live system, not from a walkthrough note.** Why: a note can have values swapped or out of date and still read as authoritative.
- **Treat the same name in another system as a different mechanism.** Check the docs before saying "X works like this here". Why: a feature called "webhooks" or "roles" in two products rarely behaves the same.
- **Don't describe what a user sees in the UI from your memory of the raw data.** Open the code that renders it and quote the mapping line. Why: the human is looking at the rendered output, and a confident wrong description reads as lying.
- **A permission or grant still showing in a list is not proof it works.** The proof is the real consumer identity exercising it (the deployed app's service account loading the page). Your own console query runs with your privileges and proves nothing. Why: expired grants can stay visible for a while.
- **A confirmed version is not confirmed behaviour.** When a fix depends on a runtime detail (cookie attributes, serialization, headers, caching), measure it on the live surface before calling it done. Why: reading the code can give the wrong diagnosis, because what the framework actually sends is not visible in the source.
- **Take a teammate's statement about themselves as ground truth.** Their own schedule, decisions, what they ordered or already did: apply it, don't run tools to confirm it. If it conflicts with a repo note, the note is stale. External facts still get checked. Why: fact-checking people about themselves wastes turns and signals distrust.

## No fabrication

- **Never invent specifics.** That covers improvement percentages, "community tests show", file paths guessed from context, config defaults, URL slugs built by analogy, API parameters and library features. Before answering a factual question about a feature, API or library, check the docs or the web; don't answer "not sure" when it can be checked. Why: a made-up default can be a no-op, a made-up URL ships broken links, and fake specifics make bad advice sound authoritative.
- **If you don't know why something exists, say so.** Grep the decision log and git history for the reason; if it isn't there, say "I don't know why". You may describe what a filter, flag or exception does, never invent why. Why: an invented rationale gets repeated and becomes "the reason".
- **Get today's date from the system (`date`), never from memory.** Write absolute dates in records; convert "yesterday" and "next Friday".
- **Never hand a human code you haven't syntax-checked or run.** At minimum `node --check file.js`, `python -m py_compile file.py`, `bash -n script.sh`, or the project's typecheck. Why: a script with a syntax error wastes the human's turn and their trust in the next one.
- **When the framework version is newer than the model's knowledge, check signatures against local docs for that exact version before writing an API call.** Why: hallucinated old APIs are guaranteed, not hypothetical. Details in [Engineering notes](engineering-notes.md).

## Numbers

- **A number goes into a conclusion only if it was read or measured.** If you derived it from code structure or "logically it should be about...", either measure it (often one count query) or label it as an estimate and list its inputs. Why: a derived number sounds like a measurement, and two unverified assumptions multiplied together give a convincing number that means nothing.
- **Sanity-check units and windows.** Per minute vs per hour, per 15-minute bucket vs total, per session vs per user, UTC vs local day.
- **Assume tools truncate without telling you.** If a query tool, search endpoint or MCP tool returns exactly a round number of rows (50, 100, 1000), treat the result as cut off: run `count(*)` or a `group by` first, then page. Search and list endpoints also tend to return the oldest items first; fetch the full objects, count and sort before concluding what is "latest". Why: a cut-off list looks complete, and you build a false conclusion on it.
- **Don't memorize counts you can derive.** "All 7 functions must be authorized" goes stale; "every file in `db/functions/`" doesn't. Why: a written-down count goes stale the next time something is added or removed.
- **Reconcile your own analytics query with the team's trusted metric before presenting it.** If they don't match, or there is nothing to compare against, present it as a draft, and write it into repo files only after a human confirms it. Why: an unreconciled query is guessing with decimals.
- **Report verification as pass/fail with the measured numbers, never "should be OK".**

## Confidence and sourcing language

- **Reserve "confirmed", "verified" and "proven" for statements an authoritative source makes explicitly.** Keep three tiers apart: "the official docs say X", "inferred from reviews or code", "community speculation". Why: an extrapolation written into a knowledge file as confirmed poisons every later session that reads it.
- **When citing a contract, spec or doc, keep the verbatim quote separate from the interpretation, and say whose interpretation it is.** For money, a request, a quote, an invoice and a payment are four different pieces of evidence; say which one you actually saw. Why: "the spec says" borrows authority that an interpretation doesn't have.
- **Use fixed confidence definitions, not feel.** High: you would merge without reading the diff. Medium: a human should skim it (no test covers the changed path, or the blast radius is unverified). Low: a check failed or an assumption can't be verified, and you must say what would raise it.
- **A short answer still carries its uncertainty.** If the open unknown is exactly what decides the yes/no, measure it first, or answer "probably not, but X is unverified". Why: cutting the caveat makes a guess look verified.

## Completeness and negative results

- **Confirm a negative search result with a second method before saying "it doesn't exist".** Search by the full name instead of an abbreviation, list instead of search, read the file instead of grepping it. Why: substring search, connectors that hide parts of a document, and case or encoding differences all produce false "missing" findings.
- **A completeness claim ("that's everything", "nothing left", "all call sites updated") requires scanning the whole source,** not just the part the question named. Why: partial checks quietly drop items that a teammate later finds.
- **Before recommending one option out of many, go through the sources you can actually reach, and say which ones you checked and which you didn't.** Why: recommending from whatever you happened to read is availability bias, and nobody can audit it.
- **When a teammate hands you a document, judge it on that document alone.** Search elsewhere for context, never for a substitute. Record missing data as "unknown". Why: substituted data makes the verdict invented.

## "Done" means verified by outcome

- **A verification is a tool call with an exit code, never a sentence.** Log every check (command, exit code, short output) as you go, and build the summary from that log rather than from memory. Why: this is what stops "tests pass" claims for tests that were never run.
- **Record a baseline (build, lint, tests) before editing.** Why: otherwise you can't tell a failure that already existed from a regression you caused. A broken baseline is noted, not silently fixed.
- **Scale rigour to risk.** Size each task (small, medium, large) and rate each touched file: green (additive, docs, tests), yellow (business logic, queries, UI state), red (auth, crypto, payments, data deletion, migrations, concurrency, public API). Red always gets the full treatment: baseline, every check, an independent review. Why: it keeps effort where the risk is and skips ceremony on typo fixes.
- **If static checks give no runtime signal, run a throwaway 3-5 line smoke script** that exercises the changed path, then delete it. If that is impossible (needs prod credentials, no simulator), say so explicitly. Why: types and lint don't catch runtime breakage.
- **Never call something done because the code looks right.** Use the feature as a user would: the happy path, an edge or stuck state, every button, a reload mid-session (state must come back), a mobile viewport. The console must be clean and the network tab free of 404s.
- **Green is not done.** CI may never build the artifact you deploy, so after a deploy: read the public health endpoint and compare its commit SHA with the commit you meant to ship, exercise the product's main flow (not just your change), and check container status and logs. Why: a build missing an environment variable can pass build, lint and deploy while the product is dead, and then a user finds it first. Pipeline details in [CI/CD and deploy](ci-cd-and-deploy.md).
- **Check that a measurement measures something.** Push an input to an extreme and confirm the output moves; treat identical results across variants as suspicious; a live check must use an input where the change is visible. Why: a "verified live" check passes trivially when the sample is already in the target format.
- **Treat an AI status report as a proposal, not a fact.** That includes your own summary, a subagent's report and another model's review. The human gate checks the outcome by clicking through the feature. For anything with access control, log in with a second test account and try to reach the first account's data. Why: the second-account check is the cheapest way to catch a data-leak bug.
- **Answer "what can go wrong here, and how would I know?" before every deploy.** If the answer is "I don't know", the change needs monitoring or a rollback plan before it ships.
- **Self-review has a ceiling.** For high-stakes changes (auth, payments, migrations, privacy, security headers), get a review from a different model, and a human pass on concurrency and timezone code, where models share blind spots. Make sure the reviewer can actually read the repo: a reviewer whose sandbox blocks file listing can report confidently on files it never saw. Reviewer agents live in [../../agents/](../../agents/).
- **When a human executes a handoff, end it by asking them to print the resulting state.** Why: a "done, it worked" report is often wrong in a detail that the printed state would show.
- **Say in one sentence what was verified and how, and what was not.** "Typecheck and 42 unit tests pass; I did not see the rendered page, so the visual check is yours." Why: the human needs to know which part of "done" is still theirs.

## Recommendations: the three-question check

Run this before delivering any technical recommendation (stack, library, pattern, command, security setup). On most teams, almost every technical recommendation is outside someone's expertise, so treat it as always on. The exception is the product owner's own domain (what users need, market conventions), where they can judge themselves.

1. **Under what concrete circumstances would this be wrong?** Name scenarios ("breaks on the edge runtime", "fails open when the provider is down"), not "it might be wrong in general".
2. **What would a world-class specialist add or correct?** A senior engineer, security engineer or SRE: what exactly would they change?
3. **How would I fact-check this?** Then do it: official docs, a second source, a quick experiment.

- **State any gap explicitly.** "I can't verify X because Y; the recommendation stands with that gap." "A specialist would probably add Z; not sure it matters at our scale." "Docs on W are thin; this is an educated guess."
- **If all three checks pass, recommend confidently,** without filler hedges. You don't need to show the process unless someone asks.
- **Measure how often a problem actually happens before proposing a tool, hook or automation against it.** An existing rule proves one incident, not recurrence, and check the base rate: a failure "concentrated in one repo" is just the base rate if that repo also accounts for a similar share of all sessions. Why: many problems that look recurring happened once, and an automation against them adds cost without removing a failure.

## Claim audit on request

When a teammate asks the agent to verify its last message (a `/verify`-style command):

1. List every factual claim and classify it: external world (API behaviour, library features, statistics), repo/files (contents, dates, numbers from docs), computation (totals, percentages, conversions), or mixed.
2. Verify each: web search or primary docs for external claims; read the actual file in full for repo claims; redo computations step by step, with a script if needed.
3. Report each claim as **Verified** (with source: URL or `file:line`), **Incorrect** (what is right, with source) or **Cannot verify** (why).
4. If the message had no factual claims, say so; don't invent verification.

Rules: don't skip a claim because you feel sure; always re-check arithmetic done "in your head" (the most commonly missed error); don't soften the result when the source contradicts you.

**After a confirmed hallucination, do a hard reset.** Name the error once, with no apology loop. Read the relevant files in full, not just their headings. Re-answer the original question with every claim backed by a file or source, and move any misfiled record to the correct file. If the error is systemic (an invented API feature, a misread repo structure), record it as a lesson; see [Lessons learned](lessons-learned.md) and [Agent setup](agent-setup.md).

## Verification stamps in repo files

Some files make claims about external systems: which workflows deploy where, the repo's branch rulesets, the database schema, a vendor API's behaviour, a provider's limits. Give those files a machine-checkable freshness stamp.

```yaml
---
verified:
  - by: agent/<model>          # or human:<handle>
    at: YYYY-MM-DDTHH:MM:SS+00:00
    how: >-
      The live check performed, e.g. gh api repos/OWNER/REPO/rulesets/ID (read-only).
stale_after: YYYY-MM-DDT00:00:00+00:00   # sooner for fast-changing systems
---
```

- **Write the stamp only after a live check, in the same commit as the content it covers.** Reading a note is not verification and is never stamped. Don't record the edit date; git has it.
- **Stamp only files that make claims about external systems.** Code, plans and internal docs don't need it.
- **Set `stale_after` by how fast that system changes:** weeks for a vendor's pricing or a SaaS API in beta, months for a stable schema.
- **List what was not verified** in the file body, so the stamp doesn't cover more than the check did.
- **In `SKILL.md` files, put the fields under `metadata:`.** Some skill uploaders reject unknown top-level keys.
- **Treat unstamped or stale claims as hearsay.** A session-start hook lists files whose `stale_after` has passed, or whose body changed in a commit after the last verification; claims from those files are notes, not checked state. Hook: [freshness-check hook](../../hooks/freshness-check.py). Template: [verified-frontmatter template](../../templates/verified-frontmatter.md).
