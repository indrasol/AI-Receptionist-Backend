-- Migration: Create Phone Numbers Table
-- Date: 2025-01-15 14:30:22
-- Description: Creates the phone_numbers table for storing VAPI phone number data
-- Environment: Runs on both dev and prod (same SQL for both environments)

-- Create the phone_numbers table if it doesn't exist
CREATE TABLE IF NOT EXISTS phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vapi_id UUID UNIQUE NOT NULL,
    org_id UUID NOT NULL,
    number VARCHAR(20) NOT NULL,
    created_at VARCHAR(50),
    updated_at VARCHAR(50),
    provider VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    provider_resource_id VARCHAR(100),
    assistant_id UUID,
    twilio_account_sid VARCHAR(100),
    name VARCHAR(255),
    workflow_id UUID
);

-- Create indexes for better performance (if they don't exist)
CREATE INDEX IF NOT EXISTS idx_phone_numbers_org_id ON phone_numbers(org_id);
CREATE INDEX IF NOT EXISTS idx_phone_numbers_number ON phone_numbers(number);
CREATE INDEX IF NOT EXISTS idx_phone_numbers_status ON phone_numbers(status);
CREATE INDEX IF NOT EXISTS idx_phone_numbers_assistant_id ON phone_numbers(assistant_id);

-- Add comments for documentation
COMMENT ON TABLE phone_numbers IS 'Stores phone numbers from VAPI API';
COMMENT ON COLUMN phone_numbers.vapi_id IS 'VAPI internal ID';
COMMENT ON COLUMN phone_numbers.org_id IS 'VAPI organization ID';
COMMENT ON COLUMN phone_numbers.number IS 'Phone number in E.164 format';
COMMENT ON COLUMN phone_numbers.provider IS 'Provider type (vapi, twilio)';
COMMENT ON COLUMN phone_numbers.status IS 'Phone number status (active, inactive)';

-- ROLLBACK INSTRUCTIONS:
-- To rollback this migration, run the following SQL:
-- DROP TABLE IF EXISTS phone_numbers;
-- Note: This will permanently delete all phone number data
