-- Create leads table for development environment
CREATE TABLE IF NOT EXISTS leads_dev (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    call_pass BOOLEAN,
    booking_success BOOLEAN
);

-- Create leads table for production environment
CREATE TABLE IF NOT EXISTS leads (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    call_pass BOOLEAN,
    booking_success BOOLEAN
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_dev_phone ON leads_dev(phone_number);
CREATE INDEX IF NOT EXISTS idx_leads_dev_created_at ON leads_dev(created_at);

CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone_number);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);

-- Enable Row Level Security (RLS)
ALTER TABLE leads_dev ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Allow all operations on leads_dev" ON leads_dev
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on leads" ON leads
    FOR ALL USING (true);

-- Add comments for documentation
COMMENT ON TABLE leads_dev IS 'Lead data from Excel uploads and API (Development)';
COMMENT ON TABLE leads IS 'Lead data from Excel uploads and API (Production)';
COMMENT ON COLUMN leads_dev.id IS 'Unique identifier for the lead';
COMMENT ON COLUMN leads_dev.first_name IS 'First name of the lead';
COMMENT ON COLUMN leads_dev.last_name IS 'Last name of the lead';
COMMENT ON COLUMN leads_dev.phone_number IS 'Phone number of the lead';
COMMENT ON COLUMN leads_dev.created_at IS 'Timestamp when the lead was created';
COMMENT ON COLUMN leads_dev.call_pass IS 'Whether the call was successful';
COMMENT ON COLUMN leads_dev.booking_success IS 'Whether the booking was successful'; 