-- Email OTPs table for storing user metadata during OTP signup/login flow
-- OTP verification is now handled by Supabase Auth, this table stores metadata only

CREATE TABLE IF NOT EXISTS email_otps (
    email TEXT PRIMARY KEY,                       -- E-mail address requesting the OTP
    otp_hash TEXT,                                -- Deprecated: OTP hash storage moved to Supabase Auth
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Expiration timestamp (UTC)
    -- Optional metadata captured during signup flow
    organization_name TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_otps_expires_at ON email_otps(expires_at);

-- Row-level security
ALTER TABLE email_otps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on email_otps" ON email_otps
    FOR ALL USING (true);
