-- Create leads table
-- Using UUID for better scalability and to avoid sequence number conflicts
CREATE TABLE IF NOT EXISTS ai_receptionist_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- UUID for better scalability
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    sheet_url TEXT,
    filename TEXT,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    import_source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_phone ON ai_receptionist_leads(phone_number);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_created_at ON ai_receptionist_leads(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_source ON ai_receptionist_leads(source);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_imported_at ON ai_receptionist_leads(imported_at);

-- Enable Row Level Security (RLS)
ALTER TABLE ai_receptionist_leads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Allow all operations on ai_receptionist_leads" ON ai_receptionist_leads
    FOR ALL USING (true);

-- Create trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for both tables
CREATE TRIGGER update_ai_receptionist_leads_updated_at 
    BEFORE UPDATE ON ai_receptionist_leads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ADD NEW COLUMNS TO EXISTING TABLES (Run these if you already have tables)
-- ============================================================================

-- Add new columns to production table
ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id),
ADD COLUMN IF NOT EXISTS created_by_user_id TEXT,
ADD COLUMN IF NOT EXISTS created_by_user_email TEXT,
ADD COLUMN IF NOT EXISTS vapi_call_id TEXT,
ADD COLUMN IF NOT EXISTS call_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS call_summary TEXT,
ADD COLUMN IF NOT EXISTS call_recording_url TEXT,
ADD COLUMN IF NOT EXISTS call_transcript TEXT;

-- Add new indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_organization_id ON ai_receptionist_leads(organization_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_created_by_user ON ai_receptionist_leads(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_vapi_call_id ON ai_receptionist_leads(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_call_status ON ai_receptionist_leads(call_status);

-- Add success_evaluation column to production table
ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS success_evaluation TEXT;

-- Add index for success_evaluation column
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_leads_success_evaluation ON ai_receptionist_leads(success_evaluation);

-- Add comments for success_evaluation column
COMMENT ON COLUMN ai_receptionist_leads.success_evaluation IS 'Evaluation of call success (e.g., "successful", "failed", "partial", "no_answer")';




-- Add organization_id to existing leads table
ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- Update existing leads to belong to CSA organization
UPDATE ai_receptionist_leads 
SET organization_id = '550e8400-e29b-41d4-a716-446655440000' 
WHERE organization_id IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_inbound_calls_organization_id ON ai_receptionist_inbound_calls(organization_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_vapi_call_id ON ai_receptionist_inbound_calls(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_phone_number ON ai_receptionist_inbound_calls(phone_number);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_created_at ON ai_receptionist_inbound_calls(created_at);


CREATE INDEX IF NOT EXISTS idx_leads_organization_id ON ai_receptionist_leads(organization_id);

-- Create index for vapi_org_id in organizations table
CREATE INDEX IF NOT EXISTS idx_organizations_vapi_org_id ON organizations(vapi_org_id); 
