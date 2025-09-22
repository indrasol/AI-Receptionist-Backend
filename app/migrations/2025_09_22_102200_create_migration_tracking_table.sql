-- Migration: Create Migration Tracking Table
-- Date: 2025-09-22 10:22:00
-- Description: Creates a table to track which migrations have been executed
-- Environment: Runs on both dev and prod (same SQL for both environments)

-- Create the migration tracking table
CREATE TABLE IF NOT EXISTS migration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_by VARCHAR(255),
    execution_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    environment VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_migration_history_name ON migration_history(migration_name);
CREATE INDEX IF NOT EXISTS idx_migration_history_executed_at ON migration_history(executed_at);
CREATE INDEX IF NOT EXISTS idx_migration_history_environment ON migration_history(environment);
CREATE INDEX IF NOT EXISTS idx_migration_history_status ON migration_history(status);

-- Add comments for documentation
COMMENT ON TABLE migration_history IS 'Tracks which migrations have been executed';
COMMENT ON COLUMN migration_history.migration_name IS 'Name of the migration file (e.g., 2025_09_22_102200_create_table.sql)';
COMMENT ON COLUMN migration_history.executed_at IS 'When the migration was executed';
COMMENT ON COLUMN migration_history.execution_time_ms IS 'How long the migration took to execute in milliseconds';
COMMENT ON COLUMN migration_history.status IS 'Migration status (success, failed, skipped)';
COMMENT ON COLUMN migration_history.environment IS 'Environment where migration was executed (dev, prod)';

-- ROLLBACK INSTRUCTIONS:
-- To rollback this migration, run the following SQL:
-- DROP TABLE IF EXISTS migration_history;
-- Note: This will permanently delete all migration tracking data
