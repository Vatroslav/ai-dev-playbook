# Database

Purpose: rules for schema changes, destructive data operations, tenant isolation, privacy-safe aggregates and correct analytical SQL.
Read when: before changing a schema, writing a migration, running a data fix or `DELETE`, adding a tenant table, writing an aggregate or report query, or handing SQL to a human.

## Access model

- **The agent's credentials on shared databases (staging, production, warehouse) are read-only.** Local and test databases are writable. Every DDL statement or data fix on a shared database is applied by a human; the agent writes the runbook and verifies the result. Why: a rule the agent "obeys" fails under pressure; a credential that can't write can't.
- **Treat any database you can reach as real data unless you created it in this session.** Smoke-test local servers on a non-default port with a temporary database, and confirm your own instance bound before sending requests that change data. Why: an orphaned dev server on the default port can answer a smoke test and change real rows.
- **Sensitive data never passes through the agent.** Diagnose from definitions (schema, view SQL, code), test on synthetic data, and have the human run queries that return only counts or aggregates. Why: everything the agent reads ends up in a transcript stored elsewhere.

## Migrations

- **Never edit a migration that has already been applied anywhere; add a new one.** Why: migration tools checksum applied files, and an edited file breaks `migrate deploy` on every environment. Test the net outcome of the migration chain instead.
- **Every schema change is a migration in the repo.** No hand-applied DDL on staging or production that the repo doesn't know about.
- **Declare protective objects where the migration tool can see them** (indexes in the ORM schema, not only in hand-written SQL). Why: an ORM generates migrations from its own schema and can drop hand-written indexes it doesn't know about.
- **Objects the ORM can't express (RLS policies, `FORCE ROW LEVEL SECURITY`, grants, CHECK constraints) get a CI guard.** Why: a migration that recreates a table silently drops them; tests still pass, protection is gone. See "Multi-tenant isolation" below.
- **Test every migration on a fresh database and on a copy of a pre-change database.** Why: `create table if not exists` and similar guards behave differently on the two, and production is always the second kind.
- **Dry-run risky migrations and data fixes inside a transaction that rolls back** (Postgres DDL is transactional):
  ```sql
  begin;
  alter table orders add column status_v2 text not null default 'open';
  update orders set status_v2 = status where status is not null;
  select status_v2, count(*) from orders group by status_v2;   -- inspect the result
  rollback;
  ```
- **Never destructive without a data path.** A table rebuild carries all rows (`insert ... select`); data you discard on purpose gets a comment, and a back-fill if needed.
- **Code that runs old and new paths in parallel during a migration carries the live-migration marker** and is not "cleaned up" before cutover. See [git workflow](git-workflow.md#staging-and-committing).
- **How migrations run in the pipeline** (staging automatically, production by a human, role separation, skip vs fail): [CI/CD and deploy](ci-cd-and-deploy.md#migrations-in-the-pipeline).

### SQLite and other startup migrations (no migration framework)

When schema init runs on every startup against the live database:

- **Every step is idempotent:** guard it with `pragma table_info`, `if not exists`, `insert or ignore`.
- **A new column goes into BOTH the fresh-schema DDL and the migration block.** Why: `create table if not exists` is a no-op on an existing table, so DDL alone leaves production broken; the migration alone leaves fresh installs broken.
- **Indexes on migrated columns are created after the migration block,** never in the fresh-schema DDL. Why: on an existing database the DDL script runs before the migration, the column doesn't exist yet, and startup crashes.
  ```python
  cols = {row[1] for row in await (await db.execute("pragma table_info(items)")).fetchall()}
  if "archived_at" not in cols:
      await db.execute("alter table items add column archived_at text default null")
  # Indexes on migrated columns: AFTER the migration block, never in the fresh-schema DDL.
  await db.execute("create index if not exists idx_items_archived on items(archived_at)")
  ```
- **A `not null` column needs a `default`** (SQLite rejects the `alter` otherwise). **Re-read `pragma table_info` before each step;** an earlier step may have rebuilt the table.
- **Changes `alter table` can't do** (drop a UNIQUE, change the primary key): create the new table, `insert ... select` all rows, drop the old one, rename, then recreate all indexes. Guard it so it runs once.
- **An upsert against a partial unique index must repeat the index's `where` clause,** or SQLite won't match the index:
  ```sql
  insert into aliases (item_id, alias) values (?, ?)
  on conflict (item_id) where item_id is not null do update set alias = excluded.alias;
  ```

## Destructive data operations

- **Every `DELETE` (and every mass `UPDATE`) runs inside a transaction with a row-count check:** count first, delete, compare the affected rows with the expectation, commit only if they match, otherwise roll back. The [delete-transaction hook](../../hooks/check-delete-transaction.sh) blocks a bare `DELETE` from the agent. A self-checking form:
  ```sql
  begin;
  select count(*) from sessions where expires_at < now() - interval '30 days';  -- say: 1204
  do $$
  declare n int;
  begin
    delete from sessions where expires_at < now() - interval '30 days';
    get diagnostics n = row_count;
    if n <> 1204 then raise exception 'expected 1204 rows, deleted %', n; end if;
  end $$;
  commit;   -- after an exception the transaction is aborted and this commit rolls back
  ```
- **Destructive operations need explicit human confirmation:** `delete`, `drop`, `truncate`, data migrations. Say what disappears, how much, and whether it can be recovered.
- **Snapshot before a manual change and diff after:** the diff must show only the intended change. Check sibling objects too (copied views, per-locale twins). Why: a bug survives in a twin copy nobody diffs.
- **Scripts that touch data block destructive actions in the script itself** (an allow-list of operations) and offer a `--dry-run` flag that prints what would change.
- **A data-deletion request (account deletion, GDPR) is closed only when every data silo is verified.** Keep a table of every location where user data lives and what deletes or anonymizes it there; check every silo unconditionally.

## Multi-tenant isolation

Two locks, because one will eventually be forgotten:

1. **App layer:** every query is scoped to the caller's tenant or user.
2. **Database backstop: Postgres row-level security.**

- **Set the tenant per transaction, not per query:** `select set_config('app.tenant_id', $1, true)` (the `true` makes it `SET LOCAL`, ending with the transaction). Why: setting it once per transaction is cheaper than per query, and a setting that outlives its transaction leaks into the next request on a pooled connection. Test that it doesn't leak.
- **Enable AND force RLS on every tenant table, with a policy that fails closed:**
  ```sql
  alter table items enable row level security;
  alter table items force row level security;   -- binds the table owner too
  create policy tenant_isolation on items
    using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
  create index items_tenant_idx on items (tenant_id);   -- declare it in the ORM schema too
  ```
  No tenant context means the comparison is null, so zero rows: fail closed. Never wrap the setting in a `coalesce` that turns "no tenant" into "all tenants".
- **Split the roles.** The app connects as a user that owns no tables and has no `BYPASSRLS`, `SUPERUSER` or `CREATEDB`. A separate owner role runs migrations. Why: without the split, RLS is not enforced; table owners and superusers bypass it unless forced.
- **No tenant table may exist without a policy, and each has a btree index with `tenant_id` as the leading column** so the policy predicate is indexable.
- **CI checks both metadata and behaviour on an ephemeral database** (see [ci.yml](../../ci/workflows/ci.yml)):
  - metadata: every table with a `tenant_id` column has RLS enabled and forced, at least one policy, and a leading `tenant_id` index;
  - behaviour, as the app role: tenant A sees only its rows; no context returns zero rows; FORCE binds the owner; inserting a row for another tenant is rejected; updating another tenant's row touches zero rows; the app role cannot disable RLS or grant itself `BYPASSRLS`; with sequential scans off, the policy uses the index.
  Why: metadata can look right while behaviour is wrong (a policy that allows everything).
- **Tables outside RLS** (for example an auth library's own user and session tables) get a lint rule that bans direct ORM access outside the one module that wires the auth library. Why: there, an unfiltered query returns other tenants' rows instead of zero.
- **Without RLS (SQLite, simple apps), every data function takes the owner ID as its first parameter and throws if it is missing.** Why: drivers bind `undefined` to `NULL`, which silently matches nothing or, with `is null` logic, everything.
- **Sharing deliberately breaks isolation.** Every new aggregate or bulk mutation decides explicitly whether shared rows count.

## Queries

- **Parameters are always bound; never interpolate IDs, emails or user input into SQL.** Identity comes from the server-side session, never from the request body or query string. More in [security](security.md).
- **Identifiers that can't be bound (table or column names in helper scripts) are checked against an allow-list or a strict pattern** such as `^[a-z0-9_]+$`.
- **Fail closed on ambiguous identity:** two rows for one email throw an error instead of binding to an arbitrary user. The same for an undeterminable date or eligibility.
- **Configuration lands where the driver reads it.** A connection-limit URL parameter that the driver adapter ignores looks like a limit and isn't; assert the value reaches the adapter.

## Privacy-safe aggregates

- **Apply minimum group sizes in the aggregation layer,** so a below-threshold row never exists and the UI can't show it by accident. Thresholds are configuration, never constants scattered in code. When a domain has several similar thresholds, name each one and always say which you mean.
- **Check every derived number:** can a single person's value, or the existence of a small group, be inferred from it, or from the difference between two published numbers (facet totals, before/after)?
- **Suppressed small groups go into a neutral "Other" bucket or are omitted, never folded into another real segment.** Why: that misreports the real segment.
- **Never group by the raw twin of a normalized column.** If a value is normalized upstream, every downstream `group by`, `join`, `partition by` and `distinct` uses the normalized column. Grouping by the raw one silently splits groups; both halves can fall under the threshold and the cell vanishes with no error. Check before a column enters a group key (must return zero rows):
  ```sql
  select d.normalized_col
    ,count(distinct d.raw_col) as raw_variants
  from source_table d
  group by d.normalized_col
  having count(distinct d.raw_col) > 1;
  ```
- **Each threshold has a test with one row that passes and one that fails it** ([testing](testing.md#prove-that-the-test-can-fail)).

## Views, pipelines and SQL handed to humans

- **Change view chains downstream-first** (the most downstream view first, the source last), so no intermediate state breaks a consumer. Re-run scheduled materialization jobs last. Views that reference columns by name need explicit edits; `select *` propagates, so check which is which.
- **Dry-run every `create or replace` against the live schema before handing it over** (run the view body as a plain `select`). Dry-run the whole view, not just the changed column: `union all` branches with hand-written `null` column lists break when a column is added or removed.
- **Change paired production and staging definitions in the same commit,** and check that the staging copy actually has every column the production object reads.
- **The repo copy of a scheduled query is not the source of truth unless it is synced.** Pull the live SQL from the job history (filtered to parent jobs, so you don't get one child statement of a multi-statement script) before concluding "this job doesn't touch X". Refresh a view's repo copy from the live DDL whenever you touch it.
- **Health probes that mirror real queries change in the same commit as the query signature.**
- **Multi-step changes (two or more objects, column changes, job re-runs) go through the [SQL runbook skill](../../skills/sql-runbook/SKILL.md):** goal, scope and what is NOT touched, measured diagnosis, deploy order with reasons, each step as full copy-paste SQL, verification queries with before and after numbers, and the doc updates after apply. The runbook keeps a "living invariants" list; append one with every change that creates one.
- **Paste the full SQL into the chat when a human applies it; don't point to a file.** Why: after the PR merges, their local file or open editor tab still holds the old version, and the old definition gets pasted over the new one.
- **Verify a manually applied object by content, not by timestamp:** a regex over the stored definition, with the new pattern present and the old one absent. A "last altered" time only proves that a paste happened.
- **A grant or permission that shows in a list is not proof that it works.** Expired entries can stay visible. Proof is the real consumer identity exercising it (the live page running as the app's service account); your own query runs with your privileges and proves nothing.
- **At the end of a human-executed step, ask the human to print the resulting state,** and report verification as PASS or FAIL with the measured numbers, never "should be fine".
- **Don't memorize counts; derive them.** "All N functions are authorized": count the files in the folder. Why: a written-down list goes stale as soon as a file is added or removed.

## Analytical query correctness

- **For boolean yes/no columns use `is true`, never `is not null`.** "No" is `false`, not `null`.
- **Start every ad-hoc query from the canonical filter or definition** (a flag column, a shared view, a documented `where` clause); never assemble your own filter combination. Why: hand-assembled filters drift from the canonical definition, and reports that claim the same population end up counting different ones.
- **For "what does the report show?" questions, query the table the report reads** (usually a materialized table), not the live view upstream of it.
- **Window functions: filter out null partition keys first.** All nulls fall into one partition, and `lag`, `first_value` or a back-fill quietly invents data across unrelated rows. Justify point-in-time versus current-state attributes with a measured difference.
- **Don't infer what a column means from its name.** Read how existing code and views use it. Why: a column that looks reusable may already be filtered or transformed for one statistic, and reusing it for another silently gives wrong results.
- **Assume query tools truncate silently.** A result of exactly the tool's cap (50, 100, 1000 rows) means "count first": run `count(*)` or a `group by`, then page.
- **"Not measured" is `null`, not 0; a measured day with no events is 0.** Days before an event existed stay null; missing days in a series are filled with 0. Exclude the team's own and test accounts from product metrics.
- **Reconcile a new analytical query with the team's existing trusted metric before presenting it.** If they don't match, or there is nothing to compare against, present it as a draft. Write it into repo docs only after a human confirms it.
