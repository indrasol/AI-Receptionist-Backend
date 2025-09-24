-- Receptionists table
CREATE TABLE IF NOT EXISTS receptionists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    assistant_name TEXT,
    phone_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Keep updated_at fresh
CREATE OR REPLACE FUNCTION update_receptionists_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_receptionists_updated_at
    BEFORE UPDATE ON receptionists
    FOR EACH ROW
    EXECUTE FUNCTION update_receptionists_updated_at();

-- Enable RLS if needed
ALTER TABLE receptionists ENABLE ROW LEVEL SECURITY;