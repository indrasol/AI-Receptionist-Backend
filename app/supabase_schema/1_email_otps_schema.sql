-- Email OTPs table for storing one-time password hashes per e-mail
-- This supports the OTP signup flow implemented in app/services/auth_service.py

CREATE TABLE IF NOT EXISTS email_otps (
    email TEXT PRIMARY KEY,                       -- E-mail address requesting the OTP
    otp_hash TEXT NOT NULL,                       -- SHA-256 hash of the 6-digit code
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Expiration timestamp (UTC)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_otps_expires_at ON email_otps(expires_at);

-- Row-level security
ALTER TABLE email_otps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on email_otps" ON email_otps
    FOR ALL USING (true);
