# RUNBOOK - <one-line problem>

**Goal:** <what must be true after>
**Scope:** <objects it changes> | **NOT touched:** <explicitly, with why>
**Dry-run validated:** <YYYY-MM-DD, method (e.g. view body run as select with limit 0 against live schema)>
**Applied by:** <who, in which console, as which account>

## Diagnosis
- Damage (measured): <query + result before>
- Since when: <known date / "unknown">
- How discovered: <report, check, user>
- Blast radius checked: <which objects searched, which patterns>

## Deploy order
<why this order; what may break in between and what must not>

## STEP 1 - <object>   (apply now)
```sql
-- full CREATE OR REPLACE statement, copy-paste ready, not a diff
```

## STEP 2 - <object>   (wait for step 1)
```sql
```

## STEP N - job re-runs   (last)
- <job name>: re-run for <range>; tables re-materialized: <list>

## Verification
1. <query> - expect <0 rows / value>. Before: <x>. Measured after: <y>. PASS/FAIL
2. <content check: stored definition contains <new pattern>, not <old pattern>>. PASS/FAIL
3. <consumer check: the app/report reads the object as its own identity>. PASS/FAIL

## Visible changes after deploy
<which numbers move for users, including already-published content the bug affected>

## Post-apply doc update
- [ ] repo SQL copies synced (sql-sync)
- [ ] diagrams / data dictionary
- [ ] deprecated-fields list
- [ ] task closed with evidence
