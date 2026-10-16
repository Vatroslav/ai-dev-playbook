---
name: data-sanity-check
description: Run the ingestion sanity check on uploaded or imported data and report anomalies - detects a source whose latest load re-sends an earlier period's file, whole (check A) or partly (check B), by comparing aggregate fingerprints. Read-only; reports, never fixes. Manual override of the scheduled run ("run the sanity check", "check the latest upload", "did source X resend old data?"). NOT for schema or view changes (use sql-runbook).
disable-model-invocation: true
---

# Data ingestion sanity check

The pattern: every recurring import (CSV uploads, partner files, nightly syncs) gets an automated read-only check that runs on a schedule, plus this skill as a manual override. The check reports; a human decides what to do.

Why: a source that resends last period's file produces no error anywhere. The numbers look plausible, every pipeline step is green, and the duplicate surfaces weeks later in a report someone already shared. Aggregate fingerprints catch it in seconds.

## Preflight

- `check.sql` (next to this file) still points at `staging.uploads` and the example columns, and the project has no such table -> `SKIP: sanity check not configured - map the table and columns in Project overrides`.
- No read-only database credentials available to the agent -> print the SQL for a human to run in the console and evaluate the pasted result.

## Steps

1. Read `check.sql`; substitute the table and column names from Project overrides.
2. Run it read-only (a read-only role or a `--dry_run`-capable client first, then the real read).
3. **0 rows** -> one sentence: `Sanity check passed - 0 anomalies (<N> sources, latest periods <list or range>)`. Get N with a `count(distinct source_id)` query; never estimate it.
4. **Rows** -> a table (format below) plus what to do:
   - A: the latest load is very likely the same file as the earlier period.
   - B: part of the latest load was reused from an earlier file or template.
   - In both cases: ask the source for a corrected file, re-run ingestion, re-run this check.

## Output format

```
Sanity check: <n> anomalies
| check | source | current period | compared with | rows | keys matching/compared |
|---|---|---|---|---|---|
| A | src_A | <period> | <period> | <n> | - |
| B | src_B | <period> | <period> | - | <k>/<n> |
Next: request new files from src_A and src_B, re-ingest, re-run this check.
```

## Headless mode

From a scheduler: run step 2, print the one-line pass or the table, exit 0 on pass and 1 on anomalies so the scheduler can alert. Alert only on a new anomaly (not one already reported for the same source and period).

## Tuning

- Check A is strict (every fingerprint identical) and has almost no false positives.
- B's 60% threshold is a starting point. Before relying on it, measure the normal share of unchanged keys between two honest periods for your data and set the threshold clearly above it. Keys with fewer than 10 rows are ignored because tiny groups repeat by chance.
- Add fingerprints that fit your data (distinct values of a categorical column, min/max dates) to `agg_stats` - never remove the strict A check.

## Dialect notes

- `period_id` must sort chronologically as stored (ISO dates or `YYYY-MM` strings, or integers).
- Postgres: if `amount` is `double precision`, write `round(avg(u.amount)::numeric, 2)`.
- BigQuery: `bigint` is a documented alias of `INT64`; qualify the table as `project.dataset.table`.
- SQLite: needs 3.39+ for `is not distinct from`.

## What NOT to do

- Don't contact sources automatically.
- Don't modify ingestion tables, jobs or the uploaded data.
- Don't update task files on your own - the human decides what is worth recording.

## Project overrides (fill in)

- Table: `<staging.uploads>`
- Columns: source `<source_id>`, period `<period_id>`, key `<item_key>`, entity `<entity_id>`, measure `<amount>`
- Schedule: `<hourly, via ...>` and where alerts go: `<channel>`
