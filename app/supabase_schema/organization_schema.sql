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

-- Inbound phone calls table
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