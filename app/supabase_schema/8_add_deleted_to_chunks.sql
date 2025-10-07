-- Add deleted column to chunks table for soft deletes
-- This allows us to mark chunks as deleted without actually removing them from the database
-- When deleted=true, the chunk should not be used and vapi_file_id should be null

ALTER TABLE chunks 
ADD COLUMN IF NOT EXISTS deleted BOOLEAN DEFAULT FALSE;

-- Create index for faster queries filtering out deleted chunks
CREATE INDEX IF NOT EXISTS idx_chunks_deleted ON chunks(deleted);

-- Create composite index for organization + deleted queries
CREATE INDEX IF NOT EXISTS idx_chunks_org_deleted ON chunks(organization_id, deleted);

-- Add comment for documentation
COMMENT ON COLUMN chunks.deleted IS 'Soft delete flag - when true, chunk is marked as deleted and should not be used';

