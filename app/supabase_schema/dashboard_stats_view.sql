-- AI Receptionist Dashboard Statistics Views
-- Separate views for development and production environments

-- =====================================================
-- PRODUCTION VIEW (uses normal tables)
-- =====================================================

create or replace view public.ai_receptionist_dashboard_view as
with 
-- Get current date and yesterday for comparisons
date_stats as (
    select 
        current_date as today,
        current_date - interval '1 day' as yesterday,
        current_date - interval '14 days' as fourteen_days_ago
),
-- Inbound calls statistics
inbound_stats as (
    select 
        o.id as organization_id,
        o.name as organization_name,
        -- Total inbound calls
        count(ic.*) as inbound_calls_total,
        -- Inbound calls today
        count(*) filter (where ic.created_at::date = (select today from date_stats)) as inbound_calls_today,
        -- Inbound calls yesterday
        count(*) filter (where ic.created_at::date = (select yesterday from date_stats)) as inbound_calls_yesterday,
        -- Inbound calls last 14 days
        count(*) filter (where ic.created_at::date >= (select fourteen_days_ago from date_stats)) as inbound_calls_last_14_days
    from public.organizations o
    left join public.ai_receptionist_inbound_calls ic on o.id = ic.organization_id
    group by o.id, o.name
),
-- Outbound calls statistics (from leads table)
outbound_stats as (
    select 
        o.id as organization_id,
        o.name as organization_name,
        -- Total outbound calls
        count(l.*) as outbound_calls_total,
        -- Outbound calls today
        count(*) filter (where l.created_at::date = (select today from date_stats)) as outbound_calls_today,
        -- Outbound calls yesterday
        count(*) filter (where l.created_at::date = (select yesterday from date_stats)) as outbound_calls_yesterday,
        -- Outbound calls last 14 days
        count(*) filter (where l.created_at::date >= (select fourteen_days_ago from date_stats)) as outbound_calls_last_14_days,
        -- Successful outbound calls (where source = 'vapi_outbound' and imported_at is recent)
        count(*) filter (where l.source = 'vapi_outbound' and l.imported_at::date >= (select today from date_stats)) as outbound_calls_successful_today,
        -- Total completed outbound calls today
        count(*) filter (where l.source = 'vapi_outbound' and l.imported_at::date = (select today from date_stats)) as outbound_calls_completed_today
    from public.organizations o
    left join public.ai_receptionist_leads l on l.source = 'vapi_outbound'  -- Only count VAPI outbound calls
    group by o.id, o.name
),
-- Daily inbound calls trend for last 14 days
daily_inbound_trend as (
    select 
        ic.organization_id,
        ic.created_at::date as call_date,
        count(*) as daily_inbound_calls
    from public.ai_receptionist_inbound_calls ic
    where ic.created_at::date >= (select fourteen_days_ago from date_stats)
    group by ic.organization_id, ic.created_at::date
),
-- Daily outbound calls trend for last 14 days
daily_outbound_trend as (
    select 
        l.organization_id,
        l.created_at::date as call_date,
        count(*) as daily_outbound_calls
    from public.ai_receptionist_leads l
    where l.source = 'vapi_outbound' and l.created_at::date >= (select fourteen_days_ago from date_stats)
    group by l.organization_id, l.created_at::date
)
-- Main dashboard view
select 
    -- Organization info
    o.id as organization_id,
    o.name as organization_name,
    
    -- Inbound calls metrics
    coalesce(ins.inbound_calls_total, 0) as inbound_calls_total,
    coalesce(ins.inbound_calls_today, 0) as inbound_calls_today,
    coalesce(ins.inbound_calls_yesterday, 0) as inbound_calls_yesterday,
    coalesce(ins.inbound_calls_last_14_days, 0) as inbound_calls_last_14_days,
    
    -- Outbound calls metrics
    coalesce(outs.outbound_calls_total, 0) as outbound_calls_total,
    coalesce(outs.outbound_calls_today, 0) as outbound_calls_today,
    coalesce(outs.outbound_calls_yesterday, 0) as outbound_calls_yesterday,
    coalesce(outs.outbound_calls_last_14_days, 0) as outbound_calls_last_14_days,
    
    -- Success rate calculations (based on today's data)
    case 
        when coalesce(outs.outbound_calls_completed_today, 0) = 0 then 0
        else round(100.0 * coalesce(outs.outbound_calls_successful_today, 0) / coalesce(outs.outbound_calls_completed_today, 1), 1)
    end as outbound_success_rate,
    
    -- Change percentages (today vs yesterday)
    case 
        when coalesce(ins.inbound_calls_yesterday, 0) = 0 then 
            case when coalesce(ins.inbound_calls_today, 0) > 0 then 100.0 else 0.0 end
        else 
            round(100.0 * (coalesce(ins.inbound_calls_today, 0) - coalesce(ins.inbound_calls_yesterday, 0)) / coalesce(ins.inbound_calls_yesterday, 1), 1)
    end as inbound_calls_change_percent,
    
    case 
        when coalesce(outs.outbound_calls_yesterday, 0) = 0 then 
            case when coalesce(outs.outbound_calls_today, 0) > 0 then 100.0 else 0.0 end
        else 
            round(100.0 * (coalesce(outs.outbound_calls_today, 0) - coalesce(outs.outbound_calls_yesterday, 0)) / coalesce(outs.outbound_calls_yesterday, 1), 1)
    end as outbound_calls_change_percent,
    
    -- Success rate change (placeholder - would need historical data)
    0.0 as success_rate_change_percent,
    
    -- Additional metrics
    coalesce(outs.outbound_calls_successful_today, 0) as outbound_calls_successful,
    coalesce(outs.outbound_calls_completed_today, 0) as outbound_calls_completed,
    
    -- Current date for reference
    (select today from date_stats) as current_date,
    (select yesterday from date_stats) as yesterday_date,
    (select fourteen_days_ago from date_stats) as fourteen_days_ago_date

from public.organizations o
left join inbound_stats ins on o.id = ins.organization_id
left join outbound_stats outs on o.id = outs.organization_id
where o.name = 'CSA';  -- Filter for CSA organization


-- =====================================================
-- DAILY TRENDS VIEWS (for charts)
-- =====================================================

-- Production daily trends view
create or replace view public.ai_receptionist_daily_trends_view as
with date_series as (
    select generate_series(
        current_date - interval '13 days',
        current_date,
        interval '1 day'
    )::date as date
),
-- Get all organizations
organizations_list as (
    select id as organization_id, name as organization_name
    from public.organizations
    where name = 'CSA'  -- Filter for CSA organization
),
-- Cross join dates with organizations
date_org_series as (
    select 
        ds.date,
        o.organization_id,
        o.organization_name
    from date_series ds
    cross join organizations_list o
),
inbound_daily as (
    select 
        ic.organization_id,
        ic.created_at::date as call_date,
        count(*) as inbound_calls
    from public.ai_receptionist_inbound_calls ic
    where ic.created_at::date >= current_date - interval '13 days'
    group by ic.organization_id, ic.created_at::date
),
outbound_daily as (
    select 
        l.organization_id,
        l.created_at::date as call_date,
        count(*) as outbound_calls
    from public.ai_receptionist_leads l
    where l.source = 'vapi_outbound' and l.created_at::date >= current_date - interval '13 days'
    group by l.organization_id, l.created_at::date
)
select 
    dos.date,
    dos.organization_id,
    dos.organization_name,
    coalesce(id.inbound_calls, 0) as inbound_calls,
    coalesce(od.outbound_calls, 0) as outbound_calls,
    coalesce(id.inbound_calls, 0) + coalesce(od.outbound_calls, 0) as total_calls
from date_org_series dos
left join inbound_daily id on dos.date = id.call_date and dos.organization_id = id.organization_id
left join outbound_daily od on dos.date = od.call_date and dos.organization_id = od.organization_id
order by dos.organization_id, dos.date; 