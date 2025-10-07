-- Migration: add receptionist_id linking to calls tables

ALTER TABLE IF EXISTS ai_receptionist_inbound_calls
  ADD COLUMN IF NOT EXISTS assistant_id UUID;
CREATE INDEX IF NOT EXISTS idx_inbound_assistant ON ai_receptionist_inbound_calls(assistant_id);

ALTER TABLE IF EXISTS ai_receptionist_leads
  ADD COLUMN IF NOT EXISTS assistant_id UUID;
CREATE INDEX IF NOT EXISTS idx_outbound_assistant ON ai_receptionist_leads(assistant_id);
