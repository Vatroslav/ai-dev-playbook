---
name: sqlite-migration
description: Change a SQLite schema safely when there is no migration framework and schema init runs on every startup against the live database - new columns, tables, indexes, constraint changes, table rebuilds. Use for ANY schema change in such a project ("add a column", "new table", "drop the unique constraint", "add an index"). Prevents the two known startup-crash traps (index before migration, upsert against a partial unique index). NOT for projects with a migration tool (Prisma, Alembic, Knex...) - follow docs/agent/database.md there.
---

# SQLite schema changes (no migration framework)

`init_db()` runs on EVERY startup against the production database, so every step must be idempotent and correctly ordered.

Why: a migration that works on a fresh dev database can crash production startup on the next deploy - and with init-on-boot, a crashed startup means the whole app is down until someone fixes it by hand.

## Preflight

- The project uses a migration tool -> `SKIP: use the migration tool (docs/agent/database.md)`.
- No copy of a pre-change production-shaped database available for step 6 -> make one from a fixture, or ask the human for a sanitized copy. Never test against the live file.

## Schema lives in two places that must agree

1. `CREATE_TABLES` (executescript, `IF NOT EXISTS`) - the schema for a FRESH database.
2. The migration block in `init_db()` - upgrades an EXISTING database.

A new column or table goes into BOTH. DDL alone leaves production broken (`CREATE TABLE IF NOT EXISTS` is a no-op on an existing table); the migration alone leaves fresh installs broken.

## Steps

1. **Adding a column** (Python + aiosqlite shown; the same shape works with `sqlite3` or `better-sqlite3`):
   ```python
   cursor = await db.execute("PRAGMA table_info(<table>)")
   columns = {row[1] for row in await cursor.fetchall()}
   if "<new_col>" not in columns:
       await db.execute("ALTER TABLE <table> ADD COLUMN <new_col> <TYPE> DEFAULT <value>")
   ```
   - A `NOT NULL` column MUST have a non-null `DEFAULT` (SQLite rejects the ALTER otherwise).
   - Re-read `PRAGMA table_info` per step - an earlier step may have rebuilt the table.

2. **Indexes on migrated columns go AFTER the migration block.** An index on a column added by a migration must NOT be in `CREATE_TABLES`: on an existing database that script runs BEFORE the migration, the column doesn't exist yet, and startup crashes. Create such indexes after the migration block with `IF NOT EXISTS`, below a comment that says why.

3. **Changes ALTER can't do** (drop a UNIQUE, change the primary key, change a column type) - rebuild:
   ```sql
   CREATE TABLE t_new (...);
   INSERT INTO t_new (...) SELECT ... FROM t;
   DROP TABLE t;
   ALTER TABLE t_new RENAME TO t;
   ```
   Guard it with a `PRAGMA table_info` / `sqlite_master` check so it runs once, inside a transaction. The rebuild drops all indexes and triggers - recreate them after the migration block. Comment any data you discard on purpose.

4. **Upsert against a partial unique index** - `ON CONFLICT(col)` must repeat the index's WHERE clause, or SQLite won't match the index:
   ```sql
   INSERT INTO aliases (item_id, name) VALUES (?, ?)
   ON CONFLICT(item_id) WHERE item_id IS NOT NULL DO UPDATE SET name = excluded.name;
   ```

5. **DELETEs run in a transaction:** BEGIN, DELETE, check the affected row count against what you expected, COMMIT only if it matches, otherwise ROLLBACK.

6. **Verify both paths before releasing:**
   - (a) fresh database: delete the local dev DB file and start the app;
   - (b) migrated database: start against a COPY of a pre-change database;
   - (c) start a second time on each - the migration must be a no-op on re-run.

## Output

```
Schema change: <what>
CREATE_TABLES updated: yes | Migration block: yes | Post-migration indexes: <list or none>
Verified: fresh DB boot OK; migrated copy boot OK; second boot no-op OK
```

## What NOT to do

- No non-idempotent step: guard everything (`PRAGMA table_info`, `IF NOT EXISTS`, `INSERT OR IGNORE`).
- No destructive change without a data path: a rebuild's `INSERT ... SELECT` carries all rows.
- No testing against the production file.
- No class or definition inserted between an existing model's fields and its validators in Python data models (the validators rebind to the new class and crash startup).
