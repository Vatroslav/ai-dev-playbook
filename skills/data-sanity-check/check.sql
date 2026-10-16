-- Ingestion sanity check. Empty result = OK. Read-only.
-- Catches a source whose LATEST load re-sends an earlier period's file, whole or in part.
--   A: every aggregate fingerprint of the latest load equals an earlier period (strict, almost no false positives).
--   B: >= 60% of keys (with n >= 10 on both sides) have an identical average vs an earlier period (partial re-use).
-- Threshold note: first measure the normal share of unchanged keys between two honest periods; set B above it.
-- Replace staging.uploads and the column names with your ingestion table (see SKILL.md, Project overrides).
-- Portable across BigQuery, Postgres and SQLite 3.39+; dialect notes in SKILL.md.
with latest as (
  select u.source_id
    ,max(u.period_id) as period_id
  from staging.uploads u
  group by 1
),key_stats as (
  select u.source_id
    ,u.period_id
    ,u.item_key
    ,count(*) as n
    ,round(avg(u.amount), 2) as avg_amount
  from staging.uploads u
  group by 1, 2, 3
),agg_stats as (
  select u.source_id
    ,u.period_id
    ,count(*) as row_count
    ,sum(u.amount) as sum_amount
    ,count(distinct u.entity_id) as distinct_entities
    ,count(distinct u.item_key) as distinct_keys
  from staging.uploads u
  group by 1, 2
),check_a as (
  select 'A' as check_type
    ,cur.source_id
    ,cur.period_id as current_period
    ,prev.period_id as compare_with
    ,cur.row_count as rows_current
    ,cast(null as bigint) as keys_matching
    ,cast(null as bigint) as keys_compared
  from agg_stats cur
  inner join latest l on l.source_id = cur.source_id
    and l.period_id = cur.period_id
  inner join agg_stats prev on prev.source_id = cur.source_id
    and prev.period_id < cur.period_id
    and prev.row_count is not distinct from cur.row_count
    and prev.sum_amount is not distinct from cur.sum_amount
    and prev.distinct_entities is not distinct from cur.distinct_entities
    and prev.distinct_keys is not distinct from cur.distinct_keys
),key_matches as (
  select cur.source_id
    ,cur.period_id as current_period
    ,prev.period_id as compare_with
    ,count(*) as keys_compared
    ,sum(case when cur.avg_amount = prev.avg_amount then 1 else 0 end) as keys_matching
  from key_stats cur
  inner join latest l on l.source_id = cur.source_id
    and l.period_id = cur.period_id
  inner join key_stats prev on prev.source_id = cur.source_id
    and prev.item_key = cur.item_key
    and prev.period_id < cur.period_id
    and cur.n >= 10
    and prev.n >= 10
  group by 1, 2, 3
),check_b as (
  select 'B' as check_type
    ,b.source_id
    ,b.current_period
    ,b.compare_with
    ,cast(null as bigint) as rows_current
    ,b.keys_matching
    ,b.keys_compared
  from key_matches b
  where b.keys_compared > 0
    and b.keys_matching * 1.0 / b.keys_compared >= 0.6
)
select * from check_a
union all
select * from check_b
order by source_id, current_period, check_type;
