-- Chunks table for storing content chunks with organization-based access
-- Each chunk represents a piece of content that can be used for AI assistant training

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('website', 'file', 'text')),
    source_id VARCHAR(500) NOT NULL, -- URL, file_id, or text_id
    name VARCHAR(200) NOT NULL, -- Short, human title for the section
    description TEXT, -- Use this content for product specifications and features or general queries
    content TEXT NOT NULL, -- The cleaned text of the chunk
    bullets JSONB, -- Array of 3-8 crisp bullets distilled from the content
    sample_questions JSONB, -- Array of 3-7 likely questions users would ask
    is_attached_to_assistant BOOLEAN DEFAULT FALSE, -- Toggle for UI - once we get query tool we need to attach to assistant
    receptionist_id UUID REFERENCES receptionists(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chunks_organization_id ON chunks(organization_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type);
CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_is_attached_to_assistant ON chunks(is_attached_to_assistant);
CREATE INDEX IF NOT EXISTS idx_chunks_created_at ON chunks(created_at);
CREATE INDEX IF NOT EXISTS idx_chunks_created_by_user_id ON chunks(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_receptionist_id ON chunks(receptionist_id);

-- Create composite index for organization + source type queries
CREATE INDEX IF NOT EXISTS idx_chunks_org_source_type ON chunks(organization_id, source_type);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_chunks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chunks_updated_at
    BEFORE UPDATE ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_chunks_updated_at();


-- Add comments for documentation
COMMENT ON TABLE chunks IS 'Stores content chunks for AI assistant training, organized by organization';
COMMENT ON COLUMN chunks.id IS 'Unique identifier for the chunk';
COMMENT ON COLUMN chunks.organization_id IS 'Organization that owns this chunk';
COMMENT ON COLUMN chunks.source_type IS 'Type of source: website, file, or text';
COMMENT ON COLUMN chunks.source_id IS 'Identifier of the source (URL, file_id, or text_id)';
COMMENT ON COLUMN chunks.name IS 'Short, human-readable title for the chunk';
COMMENT ON COLUMN chunks.description IS 'Description of what this chunk is used for';
COMMENT ON COLUMN chunks.content IS 'The actual cleaned text content of the chunk';
COMMENT ON COLUMN chunks.bullets IS 'Array of key bullet points extracted from content';
COMMENT ON COLUMN chunks.sample_questions IS 'Array of sample questions this chunk can answer';
COMMENT ON COLUMN chunks.is_attached_to_assistant IS 'Toggle for UI - whether chunk is attached to AI assistant';
COMMENT ON COLUMN chunks.created_at IS 'Timestamp when chunk was created';
COMMENT ON COLUMN chunks.updated_at IS 'Timestamp when chunk was last updated';
COMMENT ON COLUMN chunks.created_by_user_id IS 'User who created this chunk';
COMMENT ON COLUMN chunks.receptionist_id IS 'Receptionist this chunk is linked to';