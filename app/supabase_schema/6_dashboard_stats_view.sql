-- Receptionist-centric Dashboard & Trend Views
-- Drops old org views and recreates them grouped by receptionist_id / assistant_id

-- 1) Dashboard view
create or replace view public.ai_receptionist_dashboard_view as
with
 date_stats as (
   select current_date                                   as today,
          current_date - interval '1 day'               as yesterday,
          current_date - interval '14 days'             as fourteen_days_ago
 ),
 inbound_stats as (
   select r.id                                         as receptionist_id,
          r.name                                       as receptionist_name,
          count(ic.*)                                  as inbound_calls_total,
          count(*) filter (where ic.created_at::date = (select today from date_stats))        as inbound_calls_today,
          count(*) filter (where ic.created_at::date = (select yesterday from date_stats))    as inbound_calls_yesterday,
          count(*) filter (where ic.created_at::date >= (select fourteen_days_ago from date_stats)) as inbound_calls_last_14_days
   from public.receptionists r
   left join public.ai_receptionist_inbound_calls ic on ic.assistant_id = r.assistant_id
   group by r.id, r.name
 ),
 outbound_stats as (
   select r.id                                         as receptionist_id,
          r.name                                       as receptionist_name,
          count(l.*)                                   as outbound_calls_total,
          count(*) filter (where l.created_at::date = (select today from date_stats))        as outbound_calls_today,
          count(*) filter (where l.created_at::date = (select yesterday from date_stats))    as outbound_calls_yesterday,
          count(*) filter (where l.created_at::date >= (select fourteen_days_ago from date_stats)) as outbound_calls_last_14_days,
          count(*) filter (where l.source = 'vapi_outbound' and l.created_at::date = (select today from date_stats) and l.call_status = 'ended') as outbound_calls_completed_today,
          count(*) filter (where l.source = 'vapi_outbound' and l.created_at::date = (select today from date_stats) and l.success_evaluation = 'true') as outbound_calls_successful_today
   from public.receptionists r
   left join public.ai_receptionist_leads l on l.assistant_id = r.assistant_id
   group by r.id, r.name
 )
select 
  r.id   as receptionist_id,
  r.name as receptionist_name,

  -- inbound
  coalesce(ins.inbound_calls_total, 0)          as inbound_calls_total,
  coalesce(ins.inbound_calls_today, 0)          as inbound_calls_today,
  coalesce(ins.inbound_calls_yesterday, 0)      as inbound_calls_yesterday,
  coalesce(ins.inbound_calls_last_14_days, 0)   as inbound_calls_last_14_days,

  -- outbound
  coalesce(outs.outbound_calls_total, 0)        as outbound_calls_total,
  coalesce(outs.outbound_calls_today, 0)        as outbound_calls_today,
  coalesce(outs.outbound_calls_yesterday, 0)    as outbound_calls_yesterday,
  coalesce(outs.outbound_calls_last_14_days, 0) as outbound_calls_last_14_days,

  -- success rate (today)
  case 
    when coalesce(outs.outbound_calls_completed_today,0)=0 then 0.0
    else round(100.0*outs.outbound_calls_successful_today / outs.outbound_calls_completed_today,1)
  end as outbound_success_rate,

  -- simple change percentages
  case when coalesce(ins.inbound_calls_yesterday,0)=0 then 0.0
       else round(100.0*(ins.inbound_calls_today-ins.inbound_calls_yesterday)/ins.inbound_calls_yesterday,1) end as inbound_calls_change_percent,
  case when coalesce(outs.outbound_calls_yesterday,0)=0 then 0.0
       else round(100.0*(outs.outbound_calls_today-outs.outbound_calls_yesterday)/outs.outbound_calls_yesterday,1) end as outbound_calls_change_percent,
  0.0 as success_rate_change_percent,

  outs.outbound_calls_successful_today as outbound_calls_successful,
  outs.outbound_calls_completed_today  as outbound_calls_completed,

  (select today from date_stats)           as current_date,
  (select yesterday from date_stats)       as yesterday_date,
  (select fourteen_days_ago from date_stats) as fourteen_days_ago_date
from public.receptionists r
left join inbound_stats  ins on r.id = ins.receptionist_id
left join outbound_stats outs on r.id = outs.receptionist_id;

-- 2) Daily trends view (14-day sparkline)
create or replace view public.ai_receptionist_daily_trends_view as
with date_series as (
  select generate_series(current_date - interval '13 days', current_date, interval '1 day')::date as date
),
 receptionists_list as (
   select id as receptionist_id, name as receptionist_name, assistant_id from public.receptionists
),
 date_rec_series as (
   select ds.date, r.receptionist_id, r.receptionist_name, r.assistant_id
   from date_series ds cross join receptionists_list r
),
 inbound_daily as (
   select ic.created_at::date as call_date, r.id as receptionist_id, count(*) as inbound_calls
   from public.ai_receptionist_inbound_calls ic
   join public.receptionists r on r.assistant_id = ic.assistant_id
   where ic.created_at::date >= current_date - interval '13 days'
   group by r.id, ic.created_at::date
),
 outbound_daily as (
   select l.created_at::date as call_date, r.id as receptionist_id, count(*) as outbound_calls
   from public.ai_receptionist_leads l
   join public.receptionists r on r.assistant_id = l.assistant_id
   where l.created_at::date >= current_date - interval '13 days'
   group by r.id, l.created_at::date
)
select drs.date,
       drs.receptionist_id,
       drs.receptionist_name,
       coalesce(id.inbound_calls,0)  as inbound_calls,
       coalesce(od.outbound_calls,0) as outbound_calls,
       coalesce(id.inbound_calls,0)+coalesce(od.outbound_calls,0) as total_calls
from date_rec_series drs
left join inbound_daily  id on id.call_date = drs.date and id.receptionist_id = drs.receptionist_id
left join outbound_daily od on od.call_date = drs.date and od.receptionist_id = drs.receptionist_id
order by drs.receptionist_name, drs.date; 