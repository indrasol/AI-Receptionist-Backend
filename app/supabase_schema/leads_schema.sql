-- Create leads table for development environment
-- Using BIGSERIAL for simple sequential IDs (1, 2, 3...) - easier to work with
CREATE TABLE IF NOT EXISTS ai_receptionist_leads_dev (
    id BIGSERIAL PRIMARY KEY,  -- Sequential numbers (1, 2, 3...)
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    sheet_url TEXT,
    filename TEXT,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    import_source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create leads table for production environment
-- Using BIGSERIAL for simple sequential IDs (1, 2, 3...) - easier to work with
CREATE TABLE IF NOT EXISTS ai_receptionist_leads (
    id BIGSERIAL PRIMARY KEY,  -- Sequential numbers (1, 2, 3...)
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    sheet_url TEXT,
    filename TEXT,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    import_source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_phone ON ai_receptionist_leads_dev(phone_number);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_created_at ON ai_receptionist_leads_dev(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_source ON ai_receptionist_leads_dev(source);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_imported_at ON ai_receptionist_leads_dev(imported_at);

CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_phone ON ai_receptionist_leads(phone_number);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_created_at ON ai_receptionist_leads(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_source ON ai_receptionist_leads(source);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_imported_at ON ai_receptionist_leads(imported_at);

-- Enable Row Level Security (RLS)
ALTER TABLE ai_receptionist_leads_dev ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_receptionist_leads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Allow all operations on ai_receptionist_leads_dev" ON ai_receptionist_leads_dev
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on ai_receptionist_leads" ON ai_receptionist_leads
    FOR ALL USING (true);

-- Add comments for documentation
COMMENT ON TABLE ai_receptionist_leads_dev IS 'AI Receptionist lead data from various sources (Development)';
COMMENT ON TABLE ai_receptionist_leads IS 'AI Receptionist lead data from various sources (Production)';

-- Column comments for development table
COMMENT ON COLUMN ai_receptionist_leads_dev.id IS 'Sequential identifier for the lead (1, 2, 3...)';
COMMENT ON COLUMN ai_receptionist_leads_dev.first_name IS 'First name of the lead';
COMMENT ON COLUMN ai_receptionist_leads_dev.last_name IS 'Last name of the lead';
COMMENT ON COLUMN ai_receptionist_leads_dev.phone_number IS 'Phone number of the lead';
COMMENT ON COLUMN ai_receptionist_leads_dev.source IS 'Source of the lead (google_sheets, csv_upload, manual)';
COMMENT ON COLUMN ai_receptionist_leads_dev.sheet_url IS 'Google Sheets URL if imported from sheets';
COMMENT ON COLUMN ai_receptionist_leads_dev.filename IS 'Filename if imported from CSV';
COMMENT ON COLUMN ai_receptionist_leads_dev.imported_at IS 'Timestamp when the lead was imported';
COMMENT ON COLUMN ai_receptionist_leads_dev.import_source IS 'Source system for the import';
COMMENT ON COLUMN ai_receptionist_leads_dev.created_at IS 'Timestamp when the lead was created in database';
COMMENT ON COLUMN ai_receptionist_leads_dev.updated_at IS 'Timestamp when the lead was last updated';

-- Column comments for production table
COMMENT ON COLUMN ai_receptionist_leads.id IS 'Sequential identifier for the lead (1, 2, 3...)';
COMMENT ON COLUMN ai_receptionist_leads.first_name IS 'First name of the lead';
COMMENT ON COLUMN ai_receptionist_leads.last_name IS 'Last name of the lead';
COMMENT ON COLUMN ai_receptionist_leads.phone_number IS 'Phone number of the lead';
COMMENT ON COLUMN ai_receptionist_leads.source IS 'Source of the lead (google_sheets, csv_upload, manual)';
COMMENT ON COLUMN ai_receptionist_leads.sheet_url IS 'Google Sheets URL if imported from sheets';
COMMENT ON COLUMN ai_receptionist_leads.filename IS 'Filename if imported from CSV';
COMMENT ON COLUMN ai_receptionist_leads.imported_at IS 'Timestamp when the lead was imported';
COMMENT ON COLUMN ai_receptionist_leads.import_source IS 'Source system for the import';
COMMENT ON COLUMN ai_receptionist_leads.created_at IS 'Timestamp when the lead was created in database';
COMMENT ON COLUMN ai_receptionist_leads.updated_at IS 'Timestamp when the lead was last updated';

-- Create trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for both tables
CREATE TRIGGER update_ai_receptionist_leads_dev_updated_at 
    BEFORE UPDATE ON ai_receptionist_leads_dev 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_receptionist_leads_updated_at 
    BEFORE UPDATE ON ai_receptionist_leads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ADD NEW COLUMNS TO EXISTING TABLES (Run these if you already have tables)
-- ============================================================================

-- Add new columns to development table
ALTER TABLE ai_receptionist_leads_dev 
ADD COLUMN IF NOT EXISTS created_by_user_id TEXT,
ADD COLUMN IF NOT EXISTS created_by_user_email TEXT,
ADD COLUMN IF NOT EXISTS vapi_call_id TEXT,
ADD COLUMN IF NOT EXISTS call_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS call_summary TEXT,
ADD COLUMN IF NOT EXISTS call_recording_url TEXT,
ADD COLUMN IF NOT EXISTS call_transcript TEXT;

-- Add new columns to production table
ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS created_by_user_id TEXT,
ADD COLUMN IF NOT EXISTS created_by_user_email TEXT,
ADD COLUMN IF NOT EXISTS vapi_call_id TEXT,
ADD COLUMN IF NOT EXISTS call_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS call_summary TEXT,
ADD COLUMN IF NOT EXISTS call_recording_url TEXT,
ADD COLUMN IF NOT EXISTS call_transcript TEXT;

-- Add new indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_created_by_user ON ai_receptionist_leads_dev(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_vapi_call_id ON ai_receptionist_leads_dev(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_call_status ON ai_receptionist_leads_dev(call_status);

CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_created_by_user ON ai_receptionist_leads(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_vapi_call_id ON ai_receptionist_leads(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_call_status ON ai_receptionist_leads(call_status);

-- Add comments for the new columns
COMMENT ON COLUMN ai_receptionist_leads_dev.created_by_user_id IS 'ID of the user who created/uploaded this lead';
COMMENT ON COLUMN ai_receptionist_leads_dev.created_by_user_email IS 'Email of the user who created/uploaded this lead';
COMMENT ON COLUMN ai_receptionist_leads_dev.vapi_call_id IS 'Unique call ID from VAPI API response';
COMMENT ON COLUMN ai_receptionist_leads_dev.call_status IS 'Status of the call (pending, scheduled, queued, ringing, in-progress, forwarding, ended, etc.)';
COMMENT ON COLUMN ai_receptionist_leads_dev.call_summary IS 'Summary of the call conversation';
COMMENT ON COLUMN ai_receptionist_leads_dev.call_recording_url IS 'URL to the call recording';
COMMENT ON COLUMN ai_receptionist_leads_dev.call_transcript IS 'Full transcript of the call conversation';

COMMENT ON COLUMN ai_receptionist_leads.created_by_user_id IS 'ID of the user who created/uploaded this lead';
COMMENT ON COLUMN ai_receptionist_leads.created_by_user_email IS 'Email of the user who created/uploaded this lead';
COMMENT ON COLUMN ai_receptionist_leads.vapi_call_id IS 'Unique call ID from VAPI API response';
COMMENT ON COLUMN ai_receptionist_leads.call_status IS 'Status of the call (pending, completed, failed, etc.)';
COMMENT ON COLUMN ai_receptionist_leads.call_summary IS 'Summary of the call conversation';
COMMENT ON COLUMN ai_receptionist_leads.call_recording_url IS 'URL to the call recording';
COMMENT ON COLUMN ai_receptionist_leads.call_transcript IS 'Full transcript of the call conversation';

-- ============================================================================
-- ADD SUCCESS EVALUATION COLUMN (Run this separately)
-- ============================================================================

-- Add success_evaluation column to development table
ALTER TABLE ai_receptionist_leads_dev 
ADD COLUMN IF NOT EXISTS success_evaluation TEXT;

-- Add success_evaluation column to production table
ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS success_evaluation TEXT;

-- Add index for success_evaluation column
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_dev_success_evaluation ON ai_receptionist_leads_dev(success_evaluation);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_success_evaluation ON ai_receptionist_leads(success_evaluation);

-- Add comments for success_evaluation column
COMMENT ON COLUMN ai_receptionist_leads_dev.success_evaluation IS 'Evaluation of call success (e.g., "successful", "failed", "partial", "no_answer")';
COMMENT ON COLUMN ai_receptionist_leads.success_evaluation IS 'Evaluation of call success (e.g., "successful", "failed", "partial", "no_answer")';


