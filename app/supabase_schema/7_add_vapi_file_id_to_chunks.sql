-- Add vapi_file_id column to chunks table to store VAPI knowledge base file IDs
-- This allows us to use VAPI's knowledge base feature instead of concatenating all content in the prompt

ALTER TABLE chunks 
ADD COLUMN IF NOT EXISTS vapi_file_id VARCHAR(255);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_chunks_vapi_file_id ON chunks(vapi_file_id);

-- Add comment for documentation
COMMENT ON COLUMN chunks.vapi_file_id IS 'VAPI knowledge base file ID returned after uploading chunk as file';

