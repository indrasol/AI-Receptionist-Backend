-- Remove is_attached_to_assistant column from chunks table
-- This column is redundant since we now use vapi_file_id to determine attachment status
-- vapi_file_id != null means attached
-- vapi_file_id == null means not attached

-- Drop the column
ALTER TABLE chunks 
DROP COLUMN IF EXISTS is_attached_to_assistant;

-- Drop the index if it exists
DROP INDEX IF EXISTS idx_chunks_is_attached_to_assistant;

-- Update comment
COMMENT ON TABLE chunks IS 'Stores content chunks for AI assistant training. Attachment status determined by presence of vapi_file_id.';

