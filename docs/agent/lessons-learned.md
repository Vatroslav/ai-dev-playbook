# Lessons learned: top 25

Purpose: The 25 lessons a team new to AI coding agents most needs, ranked by how much damage ignoring them causes, each linked to the doc with the details.
Read when: onboarding a new teammate, before a first real project with an agent, or when deciding which rule to enforce first.

Each lesson guards against a common failure. The pattern behind almost all of them: an agent is fast, confident and plausible, so its mistakes look like progress until someone checks the outcome.

1. **Verify before claiming; never fabricate.** Numbers, file paths, URLs, config defaults and API features must be read or measured, or explicitly labelled as estimates; claims about external systems come from a live check, not old notes. Why: the team treats what the agent says as fact, and a made-up default or URL ships as a bug. [Verification](verification.md)

2. **Green is not done.** After a deploy, compare the live health endpoint's SHA with the commit you meant to ship, use the product's main flow, and read container status and logs. Why: a build missing an environment variable can pass build, lint and deploy while the product is dead, and then a user finds it first. [Verification](verification.md), [CI/CD and deploy](ci-cd-and-deploy.md)

3. **An AI status report is a proposal, and self-review has a ceiling.** Check outcomes by using the feature, test access control with a second account, and get a different model plus a human to review auth, payment, concurrency and timezone code. Why: a model reviewing its own diff confirms what it meant, not what is there. [Verification](verification.md)

4. **Debug on real data and in the real context before writing a fix.** Trace data to its source, reproduce UI bugs inside their real parents, and measure per unit instead of trusting one event that lines up in time. Why: a cause guessed from timing or from the wrong context gets a fix that changes nothing, while the real cause (often one slow query, one user or one tenant) stays. [Debugging](debugging.md)

5. **Two fix attempts, then revert and report; a test failing twice is about the environment.** Look for zombie servers, port clashes, unseeded databases and hot reloads before rerunning. Why: rerunning a test that fails for environmental reasons burns hours while the code is already correct. [Debugging](debugging.md)

6. **Prove the test catches the bug, and test against realistic data.** Run the new test against the unfixed code and watch it fail; prefer real data sources and real servers over idealized mocks. Why: a test written after the fix may pass with or without it, and mocks hide sparse-data and overlap bugs. [Debugging](debugging.md), [Testing](testing.md)

7. **Keep scope tight.** Fix exactly what was flagged plus the same defect wherever it recurs, ask before removing anything, and treat a question as a question. Why: widened fixes change things people were happy with, and removals are expensive to undo. [Collaboration](collaboration.md)

8. **Explore options and get an explicit "go" before building.** Lay out alternatives, sketch the design, and ask how a workflow really works before automating it. Why: building early skips the team's decision, and new criteria regularly overturn the first favourite. [Collaboration](collaboration.md)

9. **The agent decides implementation; the product owner decides product.** The agent picks libraries and structure and explains them in one line; names, flows, rules and copy meaning are the owner's call, with options and consequences laid out first. Why: menus of technical options burden non-experts, and an agent that "decides" product questions pushes the team out of its own product. [Collaboration](collaboration.md)

10. **Parallel sessions and teammates share the repo, so give each its own worktree and stage by name.** Commit with an explicit pathspec (`git commit -m "..." -- file1 file2`), and fetch and check open PRs before implementing. Why: a path-less commit sweeps other sessions' staged files into the wrong PR, and skipping the check gets the same feature implemented twice. [Git workflow](git-workflow.md)

11. **The agent has no production access.** The agent gets no production credentials, no SSH and no prod deploys; a human runs production commands from a structured handoff, and the agent refuses "just this once" requests to bypass that. Why: rules an agent merely obeys fail under pressure, while missing credentials don't. [Security](security.md), [CI/CD and deploy](ci-cd-and-deploy.md)

12. **Secrets and sensitive data never pass through the agent.** No printing tokens, no reading `.env` "to help", no peeking at customer data; the agent writes the tool, the human runs it, and it prints counts, not values. Why: everything the agent reads ends up in a transcript on someone else's server. [Security](security.md)

13. **Rules that must always hold belong in hooks, lint and CI, not in prose.** When a written rule has failed two or three times, promote it to a mechanical gate. Why: models drift from instructions over long sessions, and a hook is enforced by the harness every time. [Agent setup](agent-setup.md), [Security](security.md)

14. **Tie guards to irreversibility, and test that they fire.** Ask before deleting untracked files or force-pushing, stay silent for temp files and tracked edits, and probe every guard regularly. Why: an over-broad guard gets switched off, and a guard with a missing dependency fails silently, which looks exactly like a guard that lets the call through. [Security](security.md)

15. **Reuse before writing, and make cleanup part of the feature.** Search for an existing helper before adding one, and delete dead code, scaffolding and `_old` files in the same commit. Why: agents add rather than consolidate, and three functions doing the same thing drift apart. [Engineering notes](engineering-notes.md)

16. **Measure before building tools or optimizing code.** Count how often a problem actually happens before adding a hook or automation, and time the existing code (wall time) before replacing it. Why: many problems that look recurring happened once, so an automation against them removes nothing, and a "smarter" algorithm can be slower than the simple one it replaces. [Verification](verification.md), [Debugging](debugging.md)

17. **Put the answer in the final message, paste deliverables in chat, and ask one yes/no question.** Agent UIs collapse interim text, and nobody opens a file mid-task. Why: an answer above a question box, or "see the runbook file", effectively never arrives. [Collaboration](collaboration.md)

18. **Commands handed to humans carry their own context.** Say where the command runs, as which account and in which folder, put `cd` as the first line, use secret prompts that name the exact account, and never put a rollback command next to a deploy. Why: a human who pastes a block runs all of it, so a rollback placed below a deploy undoes the deploy right after it succeeds. [Collaboration](collaboration.md)

19. **Write decisions down the moment they are made, with their why.** Record them in the tracker or decision log and commit; trackers hold the concrete trigger for an action, not a status label like "waiting". Why: unrecorded decisions come back as fresh questions every session. [Planning and tracking](planning-and-tracking.md), [Collaboration](collaboration.md)

20. **Keep agent instructions lean and findable.** The root instruction file holds what every session needs, plus pointers to on-demand docs; each fact lives in one file and the rest point to it. Why: a fact scattered across files with no pointer gets missed, and the agent then claims "it isn't written anywhere". [Agent setup](agent-setup.md)

21. **Make every deploy identifiable.** Bump the version by intent (feat, fix, breaking) in the same commit, and expose version plus short SHA in a health endpoint. Why: without the SHA, "is my change live?" has no answer, and debugging a stale deploy wastes hours. [Versioning](versioning.md)

22. **Treat database migrations as the riskiest change you make.** Dry-run them in a transaction, have the pipeline apply or verify them, never edit an applied migration, and make a skipped step look different from a failed one. Why: a green pipeline can ship code against an unmigrated schema. [Database](database.md)

23. **Know the shell traps, and check bytes, not appearances.** Backticks in commit messages, Git Bash `/flag` conversion, heredoc escapes turning into raw bytes, CRLF scripts, and interactive prompts that hang the agent. Why: they all fail silently, and pushed history can't be fixed without a force push. [Shell and environment](shell-and-environment.md)

24. **Scale rigour to risk.** Size each task and rate touched files; auth, payments, deletion, migrations and concurrency always get a baseline, every check and an independent review, while typo fixes get none of that. Why: uniform ceremony gets skipped everywhere, including where it matters. [Verification](verification.md)

25. **Analysis and metrics must serve a decision.** Before building a dashboard or deepening an analysis, name the decision that could change, and exclude your own and test accounts from the numbers. Why: in a small sample, the team's own test traffic is enough to flip the conclusion. [Planning and tracking](planning-and-tracking.md)
