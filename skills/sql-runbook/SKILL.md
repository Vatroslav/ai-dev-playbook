---
name: sql-runbook
description: Playbook for multi-step changes to a SQL view/job chain in a database or warehouse - views that read views, scheduled queries that materialize tables, column changes, pipeline bug fixes. The agent diagnoses on real data, writes a runbook with full copy-paste SQL in deploy order, a human applies it, the agent verifies with measured numbers. Use for any change touching 2+ views/tables, changing columns, needing a job re-run, or fixing wrong numbers in a report ("fix the view", "add a column to the pipeline", "the dashboard shows wrong totals"). NOT for app schema migrations (docs/agent/database.md) and NOT for syncing repo copies (sql-sync).
argument-hint: "[change description]"
---

# SQL runbook

Why: view chains fail between steps. Apply the source view first and every downstream view breaks until the rest lands; re-run a job too early and it materializes the old logic; paste a stale local file and the fix silently reverts. A runbook fixes the order, carries the full SQL, and ends with measured verification.

## Hard limits

- The agent's database credentials are read-only. Every DDL statement and job re-run is applied by a human in the console. The agent writes the runbook and verifies.
- Diagnose on real data and real columns before writing a fix (schema queries, sample selects). Never build a fix on an assumed structure.
- Blast radius: check sibling views that share the logic or columns. Fix the same defect where it recurs; don't start a proactive audit of everything.

## Preflight

- Repo copies of the affected views may be stale -> run sql-sync for each affected view first.
- Only one object changes and no job re-run is needed -> a short handoff is enough; still dry-run and verify.

## How the chain behaves (it decides the order)

- Views are read live (view -> view); materialization goes through scheduled jobs (view -> table).
- Order the steps so no intermediate state breaks a consumer:
  - a change that ADDS a column: upstream-first (source, then each consumer) - a consumer can't reference a column that doesn't exist yet;
  - a change that REMOVES a column or changes what a consumer depends on: downstream-first (stop every consumer using it, then change the source);
  - a rename is add-new, switch consumers, remove-old - in two runbooks if anything outside the chain reads it.
  Write the reason for the chosen order into the runbook.
- Postgres: `create or replace view` can only append columns; dropping, renaming, reordering or retyping one means drop-and-recreate, and dependent views must be dropped and recreated with it, inside one transaction.
- Job re-runs go LAST.
- Only views that reference columns by name need explicit edits; `select *` / `t.*` propagate automatically. Check which is which (repo copies plus live DDL).
- Dry-run every `create or replace` against the live schema before handoff (run the view body as a select with a limit, or use the warehouse's dry-run mode).

## Steps

1. **Diagnose.** Measure the damage with a query (counts before), find since when, record how it was discovered, search sibling objects for the same pattern.
2. **Write the runbook** next to the SQL in the repo from `runbook-template.md`: goal, scope and what is NOT touched, diagnosis, deploy order with the reason, one STEP per object with the FULL SQL (not a diff), job re-runs, verification queries with expected results.
3. **Dry-run** each step against the live schema; record the date and method in the runbook.
4. **Hand over in chat.** Paste the full SQL of each step into the chat (never "see the file" - the human's local copy or open editor tab may be stale), in order, each marked "apply now" or "wait for step N", with where it runs and as which account (`docs/agent/collaboration.md`).
5. **Verify after apply.** Run the verification queries; report PASS/FAIL with the measured numbers, never "should be fine". Verify a manually applied object by its content (the new pattern present and the old one absent in the stored definition), not by its last-modified timestamp.
6. **Post-apply.** Sync repo copies (sql-sync), update diagrams and docs, close the task with the evidence (work-log).

## Rules that recur

**Group by the normalized form, never the raw one.** When a value is normalized or translated upstream, every downstream `group by`, `join`, `partition by` and `distinct` must use the normalized column. Grouping by the raw twin silently splits groups; both halves can fall below a minimum-count threshold and the cell vanishes with no error. Check before a column enters a group key (must return 0 rows):

```sql
select d.normalized_col
  ,count(distinct d.raw_col) as raw_variants
from source_table d
group by d.normalized_col
having count(distinct d.raw_col) > 1;
```

Normalize before lookup joins; never add duplicate rows to a lookup table (it fans out joins).

**Permissions are proven by the real consumer.** "The grant is on the list" is not proof; neither is your own query, which runs with your privileges. Proof is the application's own identity reading the object (the live page loading).

**Health probes that mirror a query change in the same runbook as the query.** A probe left on the old signature raises false alarms, and false alarms train people to ignore real ones.

**Paired environments change together.** If staging and production each have a copy of the view, change both in the same runbook and check the staging data actually contains every column the production object reads.

## Living invariants (append one for every change that creates one)

- Boolean yes/no columns: filter with `is true`, never `is not null` ("no" is false, not null).
- `union all` branches with hand-written `null` column lists must be recounted on every column add/remove; dry-run the whole view, not just the changed column.
- Every ad-hoc query starts from the project's canonical filter definition; never assemble your own filter combination.
- `<invariant> - <why> - <where it applies>`

## Output

The runbook path, then in chat: the steps in order with full SQL, and after apply a verification table:

```
| # | check | expected | before | after | result |
|---|---|---|---|---|---|
| 1 | rows with split groups | 0 | <n> | 0 | PASS |
```

## What NOT to do

- No DDL or job re-run executed by the agent.
- No "see runbook.sql" instead of pasted SQL.
- No verification by timestamp.
- No "should be fine" - numbers or it didn't happen.

## Project overrides (fill in)

- Where runbooks live: `<db/runbooks/>`
- Console where humans apply SQL, and as which account: `<warehouse web console, account ...>`
- Dry-run method: `<bq query --dry_run | explain | run the body with limit 0>`
- Canonical filter definition: `<view or CTE name>`
