create sequence "public"."ai_receptionist_leads_id_seq";

create sequence "public"."ai_receptionist_reach_id_seq";

create table "public"."ai_receptionist_inbound_calls" (
    "id" uuid not null default gen_random_uuid(),
    "first_name" character varying(255),
    "last_name" character varying(255),
    "phone_number" character varying(50) not null,
    "organization_id" uuid not null,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "vapi_call_id" character varying(255),
    "call_status" character varying(100),
    "call_summary" text,
    "call_recording_url" text,
    "call_transcript" text,
    "success_evaluation" character varying(50),
    "call_type" character varying(100),
    "call_duration_seconds" numeric(10,3),
    "call_cost" numeric(10,4),
    "ended_reason" character varying(255),
    "customer_number" character varying(50),
    "phone_number_id" character varying(255)
);


create table "public"."ai_receptionist_leads" (
    "id" bigint not null default nextval('ai_receptionist_leads_id_seq'::regclass),
    "first_name" text not null,
    "last_name" text not null,
    "phone_number" text not null,
    "source" text not null default 'manual'::text,
    "sheet_url" text,
    "filename" text,
    "imported_at" timestamp with time zone default now(),
    "import_source" text not null default 'manual'::text,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "created_by_user_id" text,
    "created_by_user_email" text,
    "vapi_call_id" text,
    "call_status" text default 'pending'::text,
    "call_summary" text,
    "call_recording_url" text,
    "call_transcript" text,
    "success_evaluation" text,
    "organization_id" uuid
);


alter table "public"."ai_receptionist_leads" enable row level security;

create table "public"."ai_receptionist_reach" (
    "id" bigint not null default nextval('ai_receptionist_reach_id_seq'::regclass),
    "name" text not null,
    "email" text not null,
    "company" text,
    "subject" text,
    "message" text,
    "channel" text[],
    "created_at" timestamp with time zone default now()
);


alter table "public"."ai_receptionist_reach" enable row level security;

create table "public"."organizations" (
    "id" uuid not null default gen_random_uuid(),
    "name" character varying(255) not null,
    "description" text,
    "vapi_org_id" character varying(255),
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
);


alter sequence "public"."ai_receptionist_leads_id_seq" owned by "public"."ai_receptionist_leads"."id";

alter sequence "public"."ai_receptionist_reach_id_seq" owned by "public"."ai_receptionist_reach"."id";

CREATE UNIQUE INDEX ai_receptionist_inbound_calls_pkey ON public.ai_receptionist_inbound_calls USING btree (id);

CREATE UNIQUE INDEX ai_receptionist_inbound_calls_vapi_call_id_key ON public.ai_receptionist_inbound_calls USING btree (vapi_call_id);

CREATE UNIQUE INDEX ai_receptionist_leads_pkey ON public.ai_receptionist_leads USING btree (id);

CREATE UNIQUE INDEX ai_receptionist_reach_pkey ON public.ai_receptionist_reach USING btree (id);

CREATE INDEX idx_ai_receptionist_leads_call_status ON public.ai_receptionist_leads USING btree (call_status);

CREATE INDEX idx_ai_receptionist_leads_created_at ON public.ai_receptionist_leads USING btree (created_at);

CREATE INDEX idx_ai_receptionist_leads_created_by_user ON public.ai_receptionist_leads USING btree (created_by_user_id);

CREATE INDEX idx_ai_receptionist_leads_imported_at ON public.ai_receptionist_leads USING btree (imported_at);

CREATE INDEX idx_ai_receptionist_leads_phone ON public.ai_receptionist_leads USING btree (phone_number);

CREATE INDEX idx_ai_receptionist_leads_source ON public.ai_receptionist_leads USING btree (source);

CREATE INDEX idx_ai_receptionist_leads_success_evaluation ON public.ai_receptionist_leads USING btree (success_evaluation);

CREATE INDEX idx_ai_receptionist_leads_vapi_call_id ON public.ai_receptionist_leads USING btree (vapi_call_id);

CREATE INDEX idx_ai_receptionist_reach_created_at ON public.ai_receptionist_reach USING btree (created_at);

CREATE INDEX idx_ai_receptionist_reach_email ON public.ai_receptionist_reach USING btree (email);

CREATE INDEX idx_inbound_calls_created_at ON public.ai_receptionist_inbound_calls USING btree (created_at);

CREATE INDEX idx_inbound_calls_organization_id ON public.ai_receptionist_inbound_calls USING btree (organization_id);

CREATE INDEX idx_inbound_calls_phone_number ON public.ai_receptionist_inbound_calls USING btree (phone_number);

CREATE INDEX idx_inbound_calls_vapi_call_id ON public.ai_receptionist_inbound_calls USING btree (vapi_call_id);

CREATE INDEX idx_leads_organization_id ON public.ai_receptionist_leads USING btree (organization_id);

CREATE INDEX idx_organizations_vapi_org_id ON public.organizations USING btree (vapi_org_id);

CREATE UNIQUE INDEX organizations_name_key ON public.organizations USING btree (name);

CREATE UNIQUE INDEX organizations_pkey ON public.organizations USING btree (id);

alter table "public"."ai_receptionist_inbound_calls" add constraint "ai_receptionist_inbound_calls_pkey" PRIMARY KEY using index "ai_receptionist_inbound_calls_pkey";

alter table "public"."ai_receptionist_leads" add constraint "ai_receptionist_leads_pkey" PRIMARY KEY using index "ai_receptionist_leads_pkey";

alter table "public"."ai_receptionist_reach" add constraint "ai_receptionist_reach_pkey" PRIMARY KEY using index "ai_receptionist_reach_pkey";

alter table "public"."organizations" add constraint "organizations_pkey" PRIMARY KEY using index "organizations_pkey";

alter table "public"."ai_receptionist_inbound_calls" add constraint "ai_receptionist_inbound_calls_organization_id_fkey" FOREIGN KEY (organization_id) REFERENCES organizations(id) not valid;

alter table "public"."ai_receptionist_inbound_calls" validate constraint "ai_receptionist_inbound_calls_organization_id_fkey";

alter table "public"."ai_receptionist_inbound_calls" add constraint "ai_receptionist_inbound_calls_vapi_call_id_key" UNIQUE using index "ai_receptionist_inbound_calls_vapi_call_id_key";

alter table "public"."ai_receptionist_leads" add constraint "ai_receptionist_leads_organization_id_fkey" FOREIGN KEY (organization_id) REFERENCES organizations(id) not valid;

alter table "public"."ai_receptionist_leads" validate constraint "ai_receptionist_leads_organization_id_fkey";

alter table "public"."organizations" add constraint "organizations_name_key" UNIQUE using index "organizations_name_key";

set check_function_bodies = off;

create or replace view "public"."ai_receptionist_daily_trends_view" as  WITH date_series AS (
         SELECT (generate_series((CURRENT_DATE - '13 days'::interval), (CURRENT_DATE)::timestamp without time zone, '1 day'::interval))::date AS date
        ), inbound_daily AS (
         SELECT ic.organization_id,
            (ic.created_at)::date AS call_date,
            count(*) AS inbound_calls
           FROM ai_receptionist_inbound_calls ic
          WHERE ((ic.created_at)::date >= (CURRENT_DATE - '13 days'::interval))
          GROUP BY ic.organization_id, ((ic.created_at)::date)
        ), outbound_daily AS (
         SELECT l.organization_id,
            (l.created_at)::date AS call_date,
            count(*) AS outbound_calls
           FROM ai_receptionist_leads l
          WHERE ((l.source = 'vapi_outbound'::text) AND ((l.created_at)::date >= (CURRENT_DATE - '13 days'::interval)))
          GROUP BY l.organization_id, ((l.created_at)::date)
        )
 SELECT ds.date,
    COALESCE(id.inbound_calls, (0)::bigint) AS inbound_calls,
    COALESCE(od.outbound_calls, (0)::bigint) AS outbound_calls,
    (COALESCE(id.inbound_calls, (0)::bigint) + COALESCE(od.outbound_calls, (0)::bigint)) AS total_calls
   FROM ((date_series ds
     LEFT JOIN inbound_daily id ON ((ds.date = id.call_date)))
     LEFT JOIN outbound_daily od ON ((ds.date = od.call_date)))
  ORDER BY ds.date;


create or replace view "public"."ai_receptionist_dashboard_view" as  WITH date_stats AS (
         SELECT CURRENT_DATE AS today,
            (CURRENT_DATE - '1 day'::interval) AS yesterday,
            (CURRENT_DATE - '14 days'::interval) AS fourteen_days_ago
        ), inbound_stats AS (
         SELECT o_1.id AS organization_id,
            o_1.name AS organization_name,
            count(ic.*) AS inbound_calls_total,
            count(*) FILTER (WHERE ((ic.created_at)::date = ( SELECT date_stats.today
                   FROM date_stats))) AS inbound_calls_today,
            count(*) FILTER (WHERE ((ic.created_at)::date = ( SELECT date_stats.yesterday
                   FROM date_stats))) AS inbound_calls_yesterday,
            count(*) FILTER (WHERE ((ic.created_at)::date >= ( SELECT date_stats.fourteen_days_ago
                   FROM date_stats))) AS inbound_calls_last_14_days
           FROM (organizations o_1
             LEFT JOIN ai_receptionist_inbound_calls ic ON ((o_1.id = ic.organization_id)))
          GROUP BY o_1.id, o_1.name
        ), outbound_stats AS (
         SELECT o_1.id AS organization_id,
            o_1.name AS organization_name,
            count(l.*) AS outbound_calls_total,
            count(*) FILTER (WHERE ((l.created_at)::date = ( SELECT date_stats.today
                   FROM date_stats))) AS outbound_calls_today,
            count(*) FILTER (WHERE ((l.created_at)::date = ( SELECT date_stats.yesterday
                   FROM date_stats))) AS outbound_calls_yesterday,
            count(*) FILTER (WHERE ((l.created_at)::date >= ( SELECT date_stats.fourteen_days_ago
                   FROM date_stats))) AS outbound_calls_last_14_days,
            count(*) FILTER (WHERE ((l.source = 'vapi_outbound'::text) AND ((l.imported_at)::date >= ( SELECT date_stats.today
                   FROM date_stats)))) AS outbound_calls_successful_today,
            count(*) FILTER (WHERE ((l.source = 'vapi_outbound'::text) AND ((l.imported_at)::date = ( SELECT date_stats.today
                   FROM date_stats)))) AS outbound_calls_completed_today
           FROM (organizations o_1
             LEFT JOIN ai_receptionist_leads l ON ((l.source = 'vapi_outbound'::text)))
          GROUP BY o_1.id, o_1.name
        ), daily_inbound_trend AS (
         SELECT ic.organization_id,
            (ic.created_at)::date AS call_date,
            count(*) AS daily_inbound_calls
           FROM ai_receptionist_inbound_calls ic
          WHERE ((ic.created_at)::date >= ( SELECT date_stats.fourteen_days_ago
                   FROM date_stats))
          GROUP BY ic.organization_id, ((ic.created_at)::date)
        ), daily_outbound_trend AS (
         SELECT l.organization_id,
            (l.created_at)::date AS call_date,
            count(*) AS daily_outbound_calls
           FROM ai_receptionist_leads l
          WHERE ((l.source = 'vapi_outbound'::text) AND ((l.created_at)::date >= ( SELECT date_stats.fourteen_days_ago
                   FROM date_stats)))
          GROUP BY l.organization_id, ((l.created_at)::date)
        )
 SELECT o.id AS organization_id,
    o.name AS organization_name,
    COALESCE(ins.inbound_calls_total, (0)::bigint) AS inbound_calls_total,
    COALESCE(ins.inbound_calls_today, (0)::bigint) AS inbound_calls_today,
    COALESCE(ins.inbound_calls_yesterday, (0)::bigint) AS inbound_calls_yesterday,
    COALESCE(ins.inbound_calls_last_14_days, (0)::bigint) AS inbound_calls_last_14_days,
    COALESCE(outs.outbound_calls_total, (0)::bigint) AS outbound_calls_total,
    COALESCE(outs.outbound_calls_today, (0)::bigint) AS outbound_calls_today,
    COALESCE(outs.outbound_calls_yesterday, (0)::bigint) AS outbound_calls_yesterday,
    COALESCE(outs.outbound_calls_last_14_days, (0)::bigint) AS outbound_calls_last_14_days,
        CASE
            WHEN (COALESCE(outs.outbound_calls_completed_today, (0)::bigint) = 0) THEN (0)::numeric
            ELSE round(((100.0 * (COALESCE(outs.outbound_calls_successful_today, (0)::bigint))::numeric) / (COALESCE(outs.outbound_calls_completed_today, (1)::bigint))::numeric), 1)
        END AS outbound_success_rate,
        CASE
            WHEN (COALESCE(ins.inbound_calls_yesterday, (0)::bigint) = 0) THEN
            CASE
                WHEN (COALESCE(ins.inbound_calls_today, (0)::bigint) > 0) THEN 100.0
                ELSE 0.0
            END
            ELSE round(((100.0 * ((COALESCE(ins.inbound_calls_today, (0)::bigint) - COALESCE(ins.inbound_calls_yesterday, (0)::bigint)))::numeric) / (COALESCE(ins.inbound_calls_yesterday, (1)::bigint))::numeric), 1)
        END AS inbound_calls_change_percent,
        CASE
            WHEN (COALESCE(outs.outbound_calls_yesterday, (0)::bigint) = 0) THEN
            CASE
                WHEN (COALESCE(outs.outbound_calls_today, (0)::bigint) > 0) THEN 100.0
                ELSE 0.0
            END
            ELSE round(((100.0 * ((COALESCE(outs.outbound_calls_today, (0)::bigint) - COALESCE(outs.outbound_calls_yesterday, (0)::bigint)))::numeric) / (COALESCE(outs.outbound_calls_yesterday, (1)::bigint))::numeric), 1)
        END AS outbound_calls_change_percent,
    0.0 AS success_rate_change_percent,
    COALESCE(outs.outbound_calls_successful_today, (0)::bigint) AS outbound_calls_successful,
    COALESCE(outs.outbound_calls_completed_today, (0)::bigint) AS outbound_calls_completed,
    ( SELECT date_stats.today
           FROM date_stats) AS "current_date",
    ( SELECT date_stats.yesterday
           FROM date_stats) AS yesterday_date,
    ( SELECT date_stats.fourteen_days_ago
           FROM date_stats) AS fourteen_days_ago_date
   FROM ((organizations o
     LEFT JOIN inbound_stats ins ON ((o.id = ins.organization_id)))
     LEFT JOIN outbound_stats outs ON ((o.id = outs.organization_id)))
  WHERE ((o.name)::text = 'CSA'::text);


CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

grant delete on table "public"."ai_receptionist_inbound_calls" to "anon";

grant insert on table "public"."ai_receptionist_inbound_calls" to "anon";

grant references on table "public"."ai_receptionist_inbound_calls" to "anon";

grant select on table "public"."ai_receptionist_inbound_calls" to "anon";

grant trigger on table "public"."ai_receptionist_inbound_calls" to "anon";

grant truncate on table "public"."ai_receptionist_inbound_calls" to "anon";

grant update on table "public"."ai_receptionist_inbound_calls" to "anon";

grant delete on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant insert on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant references on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant select on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant trigger on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant truncate on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant update on table "public"."ai_receptionist_inbound_calls" to "authenticated";

grant delete on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant insert on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant references on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant select on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant trigger on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant truncate on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant update on table "public"."ai_receptionist_inbound_calls" to "service_role";

grant delete on table "public"."ai_receptionist_leads" to "anon";

grant insert on table "public"."ai_receptionist_leads" to "anon";

grant references on table "public"."ai_receptionist_leads" to "anon";

grant select on table "public"."ai_receptionist_leads" to "anon";

grant trigger on table "public"."ai_receptionist_leads" to "anon";

grant truncate on table "public"."ai_receptionist_leads" to "anon";

grant update on table "public"."ai_receptionist_leads" to "anon";

grant delete on table "public"."ai_receptionist_leads" to "authenticated";

grant insert on table "public"."ai_receptionist_leads" to "authenticated";

grant references on table "public"."ai_receptionist_leads" to "authenticated";

grant select on table "public"."ai_receptionist_leads" to "authenticated";

grant trigger on table "public"."ai_receptionist_leads" to "authenticated";

grant truncate on table "public"."ai_receptionist_leads" to "authenticated";

grant update on table "public"."ai_receptionist_leads" to "authenticated";

grant delete on table "public"."ai_receptionist_leads" to "service_role";

grant insert on table "public"."ai_receptionist_leads" to "service_role";

grant references on table "public"."ai_receptionist_leads" to "service_role";

grant select on table "public"."ai_receptionist_leads" to "service_role";

grant trigger on table "public"."ai_receptionist_leads" to "service_role";

grant truncate on table "public"."ai_receptionist_leads" to "service_role";

grant update on table "public"."ai_receptionist_leads" to "service_role";

grant delete on table "public"."ai_receptionist_reach" to "anon";

grant insert on table "public"."ai_receptionist_reach" to "anon";

grant references on table "public"."ai_receptionist_reach" to "anon";

grant select on table "public"."ai_receptionist_reach" to "anon";

grant trigger on table "public"."ai_receptionist_reach" to "anon";

grant truncate on table "public"."ai_receptionist_reach" to "anon";

grant update on table "public"."ai_receptionist_reach" to "anon";

grant delete on table "public"."ai_receptionist_reach" to "authenticated";

grant insert on table "public"."ai_receptionist_reach" to "authenticated";

grant references on table "public"."ai_receptionist_reach" to "authenticated";

grant select on table "public"."ai_receptionist_reach" to "authenticated";

grant trigger on table "public"."ai_receptionist_reach" to "authenticated";

grant truncate on table "public"."ai_receptionist_reach" to "authenticated";

grant update on table "public"."ai_receptionist_reach" to "authenticated";

grant delete on table "public"."ai_receptionist_reach" to "service_role";

grant insert on table "public"."ai_receptionist_reach" to "service_role";

grant references on table "public"."ai_receptionist_reach" to "service_role";

grant select on table "public"."ai_receptionist_reach" to "service_role";

grant trigger on table "public"."ai_receptionist_reach" to "service_role";

grant truncate on table "public"."ai_receptionist_reach" to "service_role";

grant update on table "public"."ai_receptionist_reach" to "service_role";

grant delete on table "public"."organizations" to "anon";

grant insert on table "public"."organizations" to "anon";

grant references on table "public"."organizations" to "anon";

grant select on table "public"."organizations" to "anon";

grant trigger on table "public"."organizations" to "anon";

grant truncate on table "public"."organizations" to "anon";

grant update on table "public"."organizations" to "anon";

grant delete on table "public"."organizations" to "authenticated";

grant insert on table "public"."organizations" to "authenticated";

grant references on table "public"."organizations" to "authenticated";

grant select on table "public"."organizations" to "authenticated";

grant trigger on table "public"."organizations" to "authenticated";

grant truncate on table "public"."organizations" to "authenticated";

grant update on table "public"."organizations" to "authenticated";

grant delete on table "public"."organizations" to "service_role";

grant insert on table "public"."organizations" to "service_role";

grant references on table "public"."organizations" to "service_role";

grant select on table "public"."organizations" to "service_role";

grant trigger on table "public"."organizations" to "service_role";

grant truncate on table "public"."organizations" to "service_role";

grant update on table "public"."organizations" to "service_role";

create policy "Allow all operations on ai_receptionist_leads"
on "public"."ai_receptionist_leads"
as permissive
for all
to public
using (true);


create policy "Allow all operations on ai_receptionist_reach"
on "public"."ai_receptionist_reach"
as permissive
for all
to public
using (true);


CREATE TRIGGER update_ai_receptionist_leads_updated_at BEFORE UPDATE ON public.ai_receptionist_leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


