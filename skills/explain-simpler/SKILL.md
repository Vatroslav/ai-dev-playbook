---
name: explain-simpler
description: Re-tell the agent's previous message more simply - same content, language that needs no prior knowledge, terms defined before use. Use on /explain-simpler, "explain that more simply", "I don't understand what you wrote", "explain like I know nothing about this". NOT for a question about one detail or a request for more information - only when someone wants the same thing, clearer.
argument-hint: "[optional: which part or term didn't land]"
---

# Explain simpler

Your last message was written for someone who already knows the system. Write it again for someone who doesn't. **Same content, different language.** Why: teammates who can't follow an explanation either approve blindly or stop asking, and both are worse than a longer message.

It is not a summary: a summary drops content; this drops only linguistic complexity, and the result may be longer.

## Scope

No argument: the whole last message. With an argument: that part or term, with enough context to stand alone.

## Order (bottom-up: define a term before you use it)

1. **In short** - one sentence: what happened, zero jargon.
2. **Concepts** - a short paragraph per concept needed later, at the level of everyday experience.
3. **Why it matters for us** - the link to this product and this decision, not general theory.
4. **The thing itself** - the bug, finding or proposal, plus the consequence: what breaks, who is affected, how urgent.
5. **What was done** - in plain words, not file names.
6. **What was not touched and what is still open** - never dropped.

## Never dropped

Every claim of the original survives: decisions waiting on the reader, alternatives, what wasn't done and why, what is unknown, risks, numbers that carry meaning.

## Dropped (address, not content)

File paths, function and package names, versions, PR and commit links, test counts, command names - unless the term itself is the point.

## Jargon and analogies

A term stays only if the reader will meet it again; then it is defined before first use. Never replace one technical term with another. An analogy must survive the next question: if it would lead to a wrong conclusion about how the thing works, describe it literally instead.

## Form

Short paragraphs, each with a bold lead-in. No tables, no nested bullets, no wall of text.

## Don't

- Paste the original with a glossary underneath.
- Write "you don't need to understand the details".
- Add new information or new work.
- Change claims to make them simpler; if the original turns out to be wrong, say so openly.
- End with "is that clearer?". If a decision is pending, end with that one yes/no question; otherwise ask nothing.

## Check before sending

Would someone who never heard of this system understand it? Is every original claim still there? Is any term used before it is explained?

## Example

Original: "The ORM adapter builds the pool with its own default max of 10; `connection_limit` in the URL is passed through as an unknown key and ignored."

Simpler:
> **In short:** the app told the database "use at most 5 connections at once", but wrote it in a place the library ignores, so the library uses its own default of 10.
>
> **What a connection pool is.** Opening a connection to the database is slow, so the app keeps a few open and lends them to requests. That set is the pool, and it has an upper limit.
>
> **Why the limit matters here.** The database accepts only a limited number of connections in total, shared by every running copy of the app, so each copy should keep its pool small.
>
> **The bug.** The library doesn't know that setting. It doesn't fail or warn; it skips it and uses its own default. Nothing breaks, and the limit is double what the config says.
