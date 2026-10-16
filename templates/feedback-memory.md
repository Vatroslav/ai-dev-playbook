<!--
Feedback file: one correction of the agent's behaviour.
Team-shared: docs/agent/feedback/<kebab-name>.md (committed, reviewed by /evolve).
Personal: the agent's memory folder (Claude Code: ~/.claude/projects/<repo>/memory/), indexed in its MEMORY.md.
Rules: durable lessons only (still true in two months?), never status. One lesson per file.
The Principle line lets /evolve merge related feedback from several people and repos into ONE rule.
/evolve sets status: DECLINED when a promotion is rejected; a declined file is never re-proposed.
-->
---
name: <kebab-name>
description: "<the rule in one line, imperative>"
metadata:
  type: feedback
  origin: <repo or area>
  # status: DECLINED   # set by /evolve; never re-proposed
---
<What happened, concretely, in one to three sentences. No customer names, no personal data, no secrets.>

**Why:** <why it matters: the cost of the failure>

**How to apply:** <the behaviour change; when it applies and when it does not>

**Principle:** <cross-cutting category, e.g. "Live-first: a claim about an external system is only as good as its last live check">

<!--
Example:

---
name: verify-deployed-sha
description: "Before saying a fix is live, compare the SHA from /api/health with the merge commit"
metadata:
  type: feedback
  origin: web-app
---
The agent reported a fix as live after the deploy workflow went green; the health endpoint still served the previous SHA because the deploy had been queued behind another run.

**Why:** a wrong "it's live" sends a teammate to test the old build and burns trust in every later report.

**How to apply:** after any deploy, curl the health endpoint and compare its sha with `git rev-parse --short <merge commit>`; report both. Not needed for docs-only merges that don't deploy.

**Principle:** Green is not done: verify the outcome on the live surface, not the pipeline status.
-->
