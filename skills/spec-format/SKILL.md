---
name: spec-format
description: Choose and apply the format for a spec, implementation plan, ADR or design doc - markdown by default, a single self-contained HTML page when the content needs diagrams, option matrices, decision trees or mockups. Use when writing or restructuring a spec, plan, ADR or design brief ("write a spec", "plan this feature", "document the options"). NOT for rules, READMEs, AGENTS.md, trackers or status notes - those are always markdown.
---

# Spec and ADR format

A spec is an investment of compute: if an agent works for hours from a misread spec, the cost is real. A plan that actually gets read beats a quick markdown file nobody reads - and a wall of HTML that reads like markdown wrapped in `<p>` tags is worse than both.

## Preflight

- No decision or feature to describe yet -> `SKIP: nothing to specify - clarify the goal first`.
- The spec fits in one sentence -> stop and ask for edge cases before writing anything (a one-sentence spec means the thinking hasn't happened).

## Steps

1. **Pick the format. Default: markdown.** Use HTML only if at least one holds:
   1. Several options with trade-off matrices (A vs B vs C).
   2. Multi-layer architecture that needs diagrams (data flow, defence in depth, pipeline stages).
   3. UI mockups or components are part of the document.
   4. A decision tree with non-linear branches.
   5. More than about 500 lines of markdown.

   Heuristic: **do I need a diagram to understand this?** Yes -> HTML. No -> markdown.

   | Document | Format |
   |---|---|
   | Short, linear ADR | Markdown |
   | ADR with A/B/C options or layered security | HTML |
   | Implementation plan for a larger feature | HTML with mockup, type interfaces, code excerpts |
   | Living design system | HTML |
   | Rules, README, AGENTS.md, tracker, status notes | Markdown, always |

2. **Write the content sections** (both formats):
   - Goal: what the user gets, in one sentence.
   - Today: current behaviour, verified live, not from memory.
   - Who is affected: every situation a user can be in, including what must NOT be revealed.
   - Constraints: locales, platforms, components to reuse, performance or privacy limits.
   - The design: shape, data, interfaces, edge cases (empty, wrong input, max length, refresh mid-flow, back button, second account).
   - Out of scope: an explicit list.
   - Acceptance criteria: a checklist the implementing agent can tick against the running build.
   - Why: enough reasoning that the next agent, six months from now, doesn't "fix" a deliberate choice.

3. **If HTML:** one self-contained file (inline CSS, no external fonts or scripts), committed next to the code it describes (`docs/specs/<slug>.html`). It must contain components that justify the format: tabs for alternatives, inline-SVG diagrams (not ASCII art), collapsible details, mockups, styled code excerpts. If it reads like markdown wrapped in `<p>` tags, convert it back.

4. **Superseded docs** get a banner at the top naming what replaced them. Never build on or cite a superseded ADR.

## Output

The file path, the chosen format and the one-line reason ("HTML: three options with a trade-off matrix"). Print the goal, out-of-scope list and acceptance criteria in chat so the reviewer doesn't have to open the file.

## What NOT to do

- No HTML for rules, READMEs, instructions or trackers.
- No external assets in HTML specs (they break offline and in review tools).
- No spec that skips "Out of scope" - agents expand scope on their own.
