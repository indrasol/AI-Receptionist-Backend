-- Scrape task tracking table
CREATE TABLE IF NOT EXISTS scrape_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    receptionist_id UUID REFERENCES receptionists(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT
);

-- Basic RLS: allow owners (organization members) to view their tasks
ALTER TABLE scrape_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Org members can view tasks" ON scrape_tasks
    FOR SELECT USING (auth.jwt() ->> 'organization_id' = organization_id::text);

-- Index to quickly fetch active tasks
CREATE INDEX IF NOT EXISTS idx_scrape_tasks_status ON scrape_tasks(status);
