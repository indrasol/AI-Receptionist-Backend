-- Simple Phone Numbers Table for VAPI Data
-- Just stores the phone number data from VAPI API response

-- Create the new table with correct structure
CREATE TABLE phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Random UUID primary key
    vapi_id UUID UNIQUE,       -- VAPI's ID (from "id" field)
    org_id UUID,              -- VAPI's orgId
    number VARCHAR(20),        -- Phone number
    created_at VARCHAR(50),    -- VAPI createdAt (as string)
    updated_at VARCHAR(50),    -- VAPI updatedAt (as string)
    provider VARCHAR(50),      -- Provider (vapi, twilio)
    status VARCHAR(20),        -- Status (active, inactive, etc)
    provider_resource_id VARCHAR(100), -- providerResourceId
    assistant_id UUID,         -- assistantId (optional)
    twilio_account_sid VARCHAR(100),   -- twilioAccountSid (optional)
    name VARCHAR(255),         -- name (optional)
    workflow_id UUID          -- workflowId (optional)
);
