-- Create contacts table
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
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_email ON ai_receptionist_reach(email);

-- Create indexes on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_ai_receptionist_reach_created_at ON ai_receptionist_reach(created_at);

-- Enable Row Level Security (RLS) on both tables
ALTER TABLE ai_receptionist_reach ENABLE ROW LEVEL SECURITY;

-- Create RLS policies to allow all operations (you can restrict this later)
CREATE POLICY "Allow all operations on ai_receptionist_reach" ON ai_receptionist_reach
    FOR ALL USING (true);