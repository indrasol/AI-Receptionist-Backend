-- -- Booking Configuration Schema for AI Receptionist
-- -- This table stores booking settings for each organization

-- CREATE TABLE IF NOT EXISTS ai_receptionist_booking_settings (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
--     -- Booking Configuration
--     booking_email VARCHAR(255) NOT NULL, -- The Outlook email for booking
--     booking_enabled BOOLEAN DEFAULT true,
--     booking_url TEXT, -- Generated booking URL
    
--     -- Booking Customization
--     booking_title VARCHAR(255) DEFAULT 'Schedule a Meeting',
--     booking_description TEXT DEFAULT 'Book a convenient time to connect with our team',
    
--     -- AI Receptionist Integration
--     auto_send_booking_link BOOLEAN DEFAULT true, -- Whether AI should automatically send booking links
--     booking_trigger_keywords TEXT[] DEFAULT ARRAY['appointment', 'meeting', 'schedule', 'book', 'calendar'], -- Keywords that trigger booking
    
--     -- Metadata
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
--     -- Ensure one booking setting per organization
--     UNIQUE(organization_id)
-- );

-- -- Create indexes for better performance
-- CREATE INDEX IF NOT EXISTS idx_booking_settings_organization_id ON ai_receptionist_booking_settings(organization_id);
-- CREATE INDEX IF NOT EXISTS idx_booking_settings_booking_email ON ai_receptionist_booking_settings(booking_email);

-- -- Enable Row Level Security (RLS)
-- ALTER TABLE ai_receptionist_booking_settings ENABLE ROW LEVEL SECURITY;

-- -- Create RLS policy to allow users to manage their organization's booking settings
-- CREATE POLICY "Users can manage their organization booking settings" ON ai_receptionist_booking_settings
--     FOR ALL 
--     USING (organization_id IN (
--         SELECT organization_id FROM users WHERE id = auth.uid()
--     ));

-- -- Function to generate booking URL
-- CREATE OR REPLACE FUNCTION generate_booking_url(booking_email TEXT)
-- RETURNS TEXT AS $$
-- BEGIN
--     RETURN 'https://outlook.office.com/book/' || booking_email || '/?ismsaljsauthenabled';
-- END;
-- $$ LANGUAGE plpgsql;

-- -- Trigger to automatically generate booking URL when booking_email is set
-- CREATE OR REPLACE FUNCTION update_booking_url()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     IF NEW.booking_email IS NOT NULL AND NEW.booking_email != '' THEN
--         NEW.booking_url := generate_booking_url(NEW.booking_email);
--         NEW.updated_at := NOW();
--     END IF;
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER trigger_update_booking_url
--     BEFORE INSERT OR UPDATE ON ai_receptionist_booking_settings
--     FOR EACH ROW
--     EXECUTE FUNCTION update_booking_url();

-- -- Insert default booking settings for CSA organization
-- INSERT INTO ai_receptionist_booking_settings (
--     organization_id, 
--     booking_email, 
--     booking_title,
--     booking_description
-- ) 
-- VALUES (
--     '550e8400-e29b-41d4-a716-446655440000', 
--     'satsbookings@indrasol.com',
--     'Schedule a Meeting with CSA',
--     'Book a convenient time to connect with the Cloud Security Alliance San Francisco Chapter team'
-- ) ON CONFLICT (organization_id) DO NOTHING;
