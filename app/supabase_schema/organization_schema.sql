-- Database Schema for AI Receptionist with Organization Support

-- Organization table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    vapi_org_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default CSA organization
INSERT INTO organizations (id, name, description, vapi_org_id) 
VALUES (
    '550e8400-e29b-41d4-a716-446655440000', 
    'CSA', 
    'Cloud Security Alliance San Francisco Chapter',
    '2fba517d-8030-49c5-9a8e-9cfbe7284d3e'
) ON CONFLICT (name) DO NOTHING;

-- Inbound phone calls table (production)
CREATE TABLE IF NOT EXISTS ai_receptionist_inbound_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(50) NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    vapi_call_id VARCHAR(255) UNIQUE,
    call_status VARCHAR(100),
    call_summary TEXT,
    call_recording_url TEXT,
    call_transcript TEXT,
    success_evaluation VARCHAR(50),
    call_type VARCHAR(100),
    call_duration_seconds DECIMAL(10,3),
    call_cost DECIMAL(10,4),
    ended_reason VARCHAR(255),
    customer_number VARCHAR(50),
    phone_number_id VARCHAR(255)
);

-- Inbound phone calls table (development)
CREATE TABLE IF NOT EXISTS ai_receptionist_inbound_calls_dev (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(50) NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    vapi_call_id VARCHAR(255) UNIQUE,
    call_status VARCHAR(100),
    call_summary TEXT,
    call_recording_url TEXT,
    call_transcript TEXT,
    success_evaluation VARCHAR(50),
    call_type VARCHAR(100),
    call_duration_seconds DECIMAL(10,3),
    call_cost DECIMAL(10,4),
    ended_reason VARCHAR(255),
    customer_number VARCHAR(50),
    phone_number_id VARCHAR(255)
);

-- Add organization_id to existing leads table
ALTER TABLE ai_receptionist_leads_dev 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

ALTER TABLE ai_receptionist_leads 
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- Update existing leads to belong to CSA organization
UPDATE ai_receptionist_leads_dev 
SET organization_id = '550e8400-e29b-41d4-a716-446655440000' 
WHERE organization_id IS NULL;

UPDATE ai_receptionist_leads 
SET organization_id = '550e8400-e29b-41d4-a716-446655440000' 
WHERE organization_id IS NULL;

-- Create indexes for better performance (production)
CREATE INDEX IF NOT EXISTS idx_inbound_calls_organization_id ON ai_receptionist_inbound_calls(organization_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_vapi_call_id ON ai_receptionist_inbound_calls(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_phone_number ON ai_receptionist_inbound_calls(phone_number);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_created_at ON ai_receptionist_inbound_calls(created_at);

-- Create indexes for better performance (development)
CREATE INDEX IF NOT EXISTS idx_inbound_calls_dev_organization_id ON ai_receptionist_inbound_calls_dev(organization_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_dev_vapi_call_id ON ai_receptionist_inbound_calls_dev(vapi_call_id);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_dev_phone_number ON ai_receptionist_inbound_calls_dev(phone_number);
CREATE INDEX IF NOT EXISTS idx_inbound_calls_dev_created_at ON ai_receptionist_inbound_calls_dev(created_at);

CREATE INDEX IF NOT EXISTS idx_leads_organization_id ON ai_receptionist_leads_dev(organization_id);
CREATE INDEX IF NOT EXISTS idx_leads_organization_id ON ai_receptionist_leads(organization_id);

-- Create index for vapi_org_id in organizations table
CREATE INDEX IF NOT EXISTS idx_organizations_vapi_org_id ON organizations(vapi_org_id); 