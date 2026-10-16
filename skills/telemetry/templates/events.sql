-- Telemetry events table for the "own backend" option (Postgres).
-- Contract columns (ts, session, env, event) are read BY NAME by every dashboard query.
-- New fields go into payload first; promote one to its own column only when a query needs it,
-- and always add columns at the end.
create table if not exists telemetry_events (
  id bigserial primary key,
  ts timestamptz not null default now(),          -- server time
  session text not null,                          -- anonymous per-device id, never a user id
  version text,
  env text not null check (env in ('dev', 'prod')),
  event text not null,
  payload jsonb not null default '{}'::jsonb,     -- non-sensitive numbers and enums only
  client_ts bigint
);
create index if not exists telemetry_events_env_event_ts on telemetry_events (env, event, ts);

-- The team's own devices, filtered out of every dashboard query.
create table if not exists telemetry_own_sessions (
  session text primary key,
  note text
);

-- Daily counts per event, prod only, own sessions excluded, missing days filled with 0,
-- days before an event first appeared as null ("not measured" is not "zero").
with base as (
  select e.ts
    ,e.event
    ,e.session
  from telemetry_events e
  left join telemetry_own_sessions o on o.session = e.session
  where e.env = 'prod'
    and o.session is null
),days as (
  select generate_series(min(ts)::date, max(ts)::date, interval '1 day')::date as day
  from base
),firsts as (
  select event
    ,min(ts)::date as first_day
  from base
  group by event
),counts as (
  select ts::date as day
    ,event
    ,count(*) as n
  from base
  group by ts::date, event
)
select d.day
  ,f.event
  ,case when d.day < f.first_day then null else coalesce(c.n, 0) end as n
from days d
cross join firsts f
left join counts c on c.day = d.day and c.event = f.event
order by d.day
  ,f.event;

-- Headline numbers: devices (not people), starts, completions.
select count(distinct e.session) as sessions
  ,count(*) filter (where e.event = 'task_started') as started
  ,count(*) filter (where e.event = 'task_finished') as finished
from telemetry_events e
left join telemetry_own_sessions o on o.session = e.session
where e.env = 'prod'
  and o.session is null;
