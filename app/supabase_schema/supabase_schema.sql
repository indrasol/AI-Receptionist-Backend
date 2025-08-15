-- Create contacts table for development environment
-- Using BIGSERIAL for simple sequential IDs (1, 2, 3...) - easier to work with
CREATE TABLE IF NOT EXISTS ai_receptionist_reach_dev (
    id BIGSERIAL PRIMARY KEY,  -- Sequential numbers (1, 2, 3...)
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    subject TEXT,
    message TEXT,
    channel TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create contacts table for production environment
-- Using BIGSERIAL for simple sequential IDs (1, 2, 3...) - easier to work with
CREATE TABLE IF NOT EXISTS ai_receptionist_reach (
    id BIGSERIAL PRIMARY KEY,  -- Sequential numbers (1, 2, 3...)
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    subject TEXT,
    message TEXT,
    channel TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_dev_email ON ai_receptionist_reach_dev(email);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_email ON ai_receptionist_reach(email);

-- Create indexes on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_dev_created_at ON ai_receptionist_reach_dev(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_created_at ON ai_receptionist_reach(created_at);

-- Enable Row Level Security (RLS) on both tables
ALTER TABLE ai_receptionist_reach_dev ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_receptionist_reach ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations (you can restrict this later)
CREATE POLICY "Allow all operations on ai_receptionist_reach_dev" ON ai_receptionist_reach_dev
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on ai_receptionist_reach" ON ai_receptionist_reach
    FOR ALL USING (true);

-- Add comments for documentation
COMMENT ON TABLE ai_receptionist_reach_dev IS 'Contact form submissions from the AI Receptionist API (Development)';
COMMENT ON TABLE ai_receptionist_reach IS 'Contact form submissions from the AI Receptionist API (Production)';
COMMENT ON COLUMN ai_receptionist_reach_dev.id IS 'Sequential identifier for the contact (1, 2, 3...)';
COMMENT ON COLUMN ai_receptionist_reach_dev.name IS 'Name of the person submitting the form';
COMMENT ON COLUMN ai_receptionist_reach_dev.email IS 'Email address of the person';
COMMENT ON COLUMN ai_receptionist_reach_dev.company IS 'Company name (optional)';
COMMENT ON COLUMN ai_receptionist_reach_dev.subject IS 'Subject of the message (optional)';
COMMENT ON COLUMN ai_receptionist_reach_dev.message IS 'Message content from the contact form (optional)';
COMMENT ON COLUMN ai_receptionist_reach_dev.channel IS 'Array of channels through which the contact was submitted (e.g., ["teams"])';
COMMENT ON COLUMN ai_receptionist_reach_dev.created_at IS 'Timestamp when the contact was submitted';

-- Add comment for production table ID as well
COMMENT ON COLUMN ai_receptionist_reach.id IS 'Sequential identifier for the contact (1, 2, 3...)'; 