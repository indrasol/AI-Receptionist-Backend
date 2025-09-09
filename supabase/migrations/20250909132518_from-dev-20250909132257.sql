drop trigger if exists "update_ai_receptionist_leads_updated_at" on "public"."ai_receptionist_leads";

drop policy "Allow all operations on ai_receptionist_leads" on "public"."ai_receptionist_leads";

alter table "public"."ai_receptionist_leads" drop constraint "ai_receptionist_leads_organization_id_fkey";

drop view if exists "public"."ai_receptionist_daily_trends_view";

drop view if exists "public"."ai_receptionist_dashboard_view";

drop index if exists "public"."idx_ai_receptionist_leads_call_status";

drop index if exists "public"."idx_ai_receptionist_leads_created_at";

drop index if exists "public"."idx_ai_receptionist_leads_created_by_user";

drop index if exists "public"."idx_ai_receptionist_leads_imported_at";

drop index if exists "public"."idx_ai_receptionist_leads_phone";

drop index if exists "public"."idx_ai_receptionist_leads_source";

drop index if exists "public"."idx_ai_receptionist_leads_success_evaluation";

drop index if exists "public"."idx_ai_receptionist_leads_vapi_call_id";

drop index if exists "public"."idx_leads_organization_id";

alter table "public"."ai_receptionist_leads" drop column "call_recording_url";

alter table "public"."ai_receptionist_leads" drop column "call_status";

alter table "public"."ai_receptionist_leads" drop column "call_summary";

alter table "public"."ai_receptionist_leads" drop column "call_transcript";

alter table "public"."ai_receptionist_leads" drop column "created_by_user_email";

alter table "public"."ai_receptionist_leads" drop column "created_by_user_id";

alter table "public"."ai_receptionist_leads" drop column "organization_id";

alter table "public"."ai_receptionist_leads" drop column "success_evaluation";

alter table "public"."ai_receptionist_leads" drop column "vapi_call_id";

alter table "public"."ai_receptionist_leads" alter column "first_name" drop not null;

alter table "public"."ai_receptionist_leads" alter column "id" set default gen_random_uuid();

alter table "public"."ai_receptionist_leads" alter column "id" set data type uuid using "id"::uuid;

alter table "public"."ai_receptionist_leads" alter column "last_name" drop not null;

alter table "public"."ai_receptionist_leads" disable row level security;

drop sequence if exists "public"."ai_receptionist_leads_id_seq";


