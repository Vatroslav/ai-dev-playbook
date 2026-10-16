---
name: sql-sync
description: Keep repo copies of database views (and the SQL of scheduled queries) in step with the live database, so git history stays usable for diagnosis. Use whenever a task touches a view that has a repo copy, when someone says they changed a view or scheduled query in the console ("I changed view X", "sync the views", "is the repo copy current?"), and before writing a sql-runbook. Read-only against the database. NOT for changing views (use sql-runbook).
---

# SQL repo sync

Repo copies of views are documentation, not the source of truth - the live database is. A stale copy makes "this view doesn't touch X" claims wrong and makes `git log` useless for "when did this logic change?".

## Preflight

- No read-only database access for the agent -> print the fetch query for a human and diff the pasted result.
- The view has no repo copy -> create one only if the task depends on it; don't mirror the whole schema proactively.

## Trigger 1: refresh-on-touch

When a task touches a view that has a repo copy:
1. Fetch the live DDL:
   - Postgres: `select pg_get_viewdef('<schema>.<view>'::regclass, true);`
   - BigQuery: `select ddl from <dataset>.INFORMATION_SCHEMA.TABLES where table_name = '<view>';`
   - SQLite: `select sql from sqlite_master where type = 'view' and name = '<view>';`
2. Normalize line endings (and trailing whitespace).
3. Diff against the repo file.
4. Different -> write the FULL definition (`create or replace view ... as ...`, not just the select) to the repo file, commit `chore(sql): sync <view> from live - <one-line description of the difference>` (stage the file by name, commit with a pathspec), and THEN continue the original task.

## Trigger 2: explicit

"I changed view X in the console" -> same procedure for X, then check whether any sibling view or job reads the changed columns.

## Scheduled-query SQL

Scheduled queries are usually not auto-synced to the repo, so their repo copy is NOT the truth - check it against the live SQL before concluding "this job doesn't touch X". Most warehouses keep each run's full SQL in job history. BigQuery example:

```sql
select j.creation_time
  ,j.job_id
  ,length(j.query) as query_chars
  ,j.query
from `region-<region>`.INFORMATION_SCHEMA.JOBS j
where j.job_id like '<scheduled job id prefix>%'
  and j.parent_job_id is null
order by j.creation_time desc
limit 5;
```

Filter to PARENT jobs: a multi-statement script also creates one child job per statement, and the newest row may be one short child statement instead of the full script. Sanity check: the parent's `query_chars` should match the size you expect for the whole script. Find the job id prefix in the job history first; don't guess it.

## Output

```
sql-sync: 3 views checked
- reporting.v_orders: in sync
- reporting.v_revenue: UPDATED from live (added column refund_amount) - committed abc1234
- reporting.v_users: no repo copy, not needed for this task
```

## What NOT to do

- No writes to the database - this skill only reads.
- No partial definitions in the repo (always the full create statement).
- No proactive audit of every view; sync only what the task touches.
