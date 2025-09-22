#!/usr/bin/env python3
"""
Migration Creation Helper Script

This script helps create new migration files with proper naming convention.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

def create_migration(description: str):
    """Create a new migration file with timestamp"""
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    
    # Create filename
    filename = f"{timestamp}_{description.lower().replace(' ', '_')}.sql"
    
    # Use single migrations directory
    migrations_dir = Path(__file__).parent
    migrations_dir.mkdir(exist_ok=True)
    
    file_path = migrations_dir / filename
    
    # Create migration template
    template = f"""-- Migration: {description}
-- Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
-- Description: {description}
-- Environment: Runs on both dev and prod (same SQL for both environments)

-- TODO: Add your SQL statements here
-- Example:
-- CREATE TABLE example_table (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- ROLLBACK INSTRUCTIONS:
-- To rollback this migration, run the following SQL:
-- DROP TABLE IF EXISTS example_table;
-- Note: This will permanently delete all data in the table
"""
    
    # Write file
    with open(file_path, 'w') as f:
        f.write(template)
    
    print(f"✅ Created migration: {file_path}")
    print(f"📝 Edit the file to add your SQL statements")
    
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Create a new migration file")
    parser.add_argument("description", help="Description of the migration")
    
    args = parser.parse_args()
    
    try:
        create_migration(args.description)
    except Exception as e:
        print(f"❌ Error creating migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
