<!--
Project section for AGENTS.md. Replace the "## Project" block in AGENTS.md with this, filled in.
Keep it short: every line loads in every session. Point to files; never copy their content here.
Rationale: docs/agent/agent-setup.md (section 1).
-->

## Project

<One paragraph: what the product is, who uses it, current stage (prototype / beta / live with N users). Who decides what: agents write code, the product owner decides product questions, teammates review.>

**The worst thing you can do here: <e.g. show one user another user's data / write to the production database / commit a secret>. If you are unsure whether an action is that, assume it is and ask first.**

A message that names no feature refers to the current milestone: <milestone name>.

### Commands

- Install: `<pnpm install --frozen-lockfile>`
- Dev server: `<pnpm dev>` (honours `PORT`)
- Test: `<pnpm test>` | DB tests: `<pnpm test:db>` | E2E: `<pnpm test:e2e>`
- Lint: `<pnpm lint>` | Typecheck: `<pnpm typecheck>` (includes test files)
- Build: `<pnpm build>`

### Sources of truth (point, don't copy)

| Topic | File | Read BEFORE |
|---|---|---|
| What we build, for whom, what not | `docs/product.md` | proposing a feature or changing scope |
| Architecture and module boundaries | `docs/architecture.md` | adding a module or crossing a boundary |
| Why things are the way they are | `docs/decisions.md`, `docs/adr/` | saying "I don't know why" or re-proposing a rejected idea |
| What's next | `docs/todo.md` | answering "what should I do" |
| Design tokens and UI rules | `DESIGN.md` | generating or changing any UI |
| API contracts | `docs/api.md` | changing a route, payload or webhook |
| Environments and deploy | `docs/infra.md` | touching CI, env vars or deploy |
| Metrics and their definitions | `docs/metrics.md` (the only place numbers live) | quoting or changing a metric |

### Where to write what

| New thing | Goes to |
|---|---|
| Action or pending decision | `/todo` skill -> `docs/todo.md` (never add rows by hand) |
| Multi-step piece of work | `/tasks` -> `docs/tasks/active/<slug>.md` plus one todo row |
| Idea for later | `docs/tasks/someday/<slug>.md` |
| Decision between alternatives | `docs/decisions.md` (big ones also `docs/adr/`) |
| Measurement, test or usage result | `docs/findings.md` (date, version, sample size) |
| Raw user or tester feedback | `docs/feedback.md` (verbatim) |
| Gotcha of an external API or service | `docs/integrations/<service>.md` |
| Correction of the agent's behaviour | `docs/agent/feedback/<name>.md` (reviewed by `/evolve`) |
| Only if nothing above fits | memory |

### Glossary

<!-- Structural terms used identically in code, docs, analytics events and chat. -->
- **<term>** - <meaning>. Never used for <the thing it gets confused with>.

### Domain rules (read in full before the matching work)

- Schema or migration change: `docs/agent/database.md`.
- Anything touching auth, permissions or personal data: `docs/agent/security.md`, then the security reviewer.
- Writes to an external service's API: plan script -> human review -> apply script.
- User-facing copy: `/humanizer` before showing the draft; every string in every locale.

### Learned

<!-- Hard-won facts about this repo, each with its reason. Add when a trap costs time; delete when the trap is gone. -->
- <fact> - Why: <what happened>.
