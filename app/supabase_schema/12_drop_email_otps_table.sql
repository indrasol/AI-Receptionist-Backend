-- Migration: Drop email_otps table
-- This table is no longer needed because metadata is now stored in Supabase Auth
-- during OTP request and automatically attached to user upon verification

-- Drop the table and its dependencies
DROP TABLE IF EXISTS email_otps CASCADE;

-- Add comment for documentation
COMMENT ON SCHEMA public IS 
  'email_otps table removed - metadata now stored in Supabase Auth user_metadata';

