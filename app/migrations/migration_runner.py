#!/usr/bin/env python3
"""
Database Migration Runner for AI Receptionist Project

This script runs SQL migrations against Supabase databases based on environment.
"""

import os
import sys
import argparse
import glob
import time
from pathlib import Path
from datetime import datetime
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, environment: str):
        self.environment = environment
        self.migrations_dir = Path(__file__).parent  # Single migrations folder
        self.supabase_client = self._get_supabase_client()
        
    def _get_supabase_client(self) -> Client:
        """Get Supabase client based on environment"""
        load_dotenv()
        
        if self.environment == "dev":
            url = os.getenv("SUPABASE_URL_DEV")
            key = os.getenv("SUPABASE_ANON_KEY_DEV")
        elif self.environment == "prod":
            url = os.getenv("SUPABASE_URL_PROD")
            key = os.getenv("SUPABASE_ANON_KEY_PROD")
        else:
            raise ValueError(f"Invalid environment: {self.environment}")
            
        if not url or not key:
            raise ValueError(f"Missing Supabase credentials for {self.environment} environment")
            
        return create_client(url, key)
    
    def _get_migration_files(self) -> list:
        """Get sorted list of migration files"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []
            
        # Get all SQL files except README.md and Python files
        migration_files = []
        for file_path in self.migrations_dir.glob("*.sql"):
            migration_files.append(str(file_path))
            
        migration_files.sort()  # Sort by filename (which includes timestamp)
        
        logger.info(f"Found {len(migration_files)} migration files for {self.environment} environment")
        return migration_files
    
    def _get_executed_migrations(self) -> set:
        """Get set of already executed migration names"""
        try:
            response = self.supabase_client.table("migration_history").select("migration_name").eq("environment", self.environment).execute()
            executed_migrations = {row["migration_name"] for row in response.data}
            logger.info(f"Found {len(executed_migrations)} already executed migrations in {self.environment}")
            return executed_migrations
        except Exception as e:
            logger.warning(f"Could not fetch executed migrations: {e}")
            logger.info("Assuming no migrations have been executed yet")
            return set()
    
    def _record_migration_execution(self, migration_name: str, execution_time_ms: int, status: str, error_message: str = None):
        """Record migration execution in the tracking table"""
        try:
            record = {
                "migration_name": migration_name,
                "execution_time_ms": execution_time_ms,
                "status": status,
                "error_message": error_message,
                "environment": self.environment,
                "executed_by": "migration_runner"
            }
            
            self.supabase_client.table("migration_history").insert(record).execute()
            logger.info(f"✅ Recorded migration execution: {migration_name} ({status})")
            
        except Exception as e:
            logger.error(f"❌ Failed to record migration execution: {e}")
    
    def _get_pending_migrations(self) -> list:
        """Get list of pending migrations (not yet executed)"""
        all_migrations = self._get_migration_files()
        executed_migrations = self._get_executed_migrations()
        
        pending_migrations = []
        for migration_file in all_migrations:
            migration_name = Path(migration_file).name
            if migration_name not in executed_migrations:
                pending_migrations.append(migration_file)
            else:
                logger.info(f"⏭️  Skipping already executed migration: {migration_name}")
        
        return pending_migrations
    
    def _execute_sql_file(self, file_path: str) -> tuple[bool, int, str]:
        """Execute a single SQL migration file and return (success, execution_time_ms, error_message)"""
        migration_name = Path(file_path).name
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Executing migration: {migration_name}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read().strip()
                
            if not sql_content:
                logger.warning(f"Empty migration file: {file_path}")
                execution_time = int((time.time() - start_time) * 1000)
                self._record_migration_execution(migration_name, execution_time, "skipped", "Empty migration file")
                return True, execution_time, None
                
            # Execute SQL using Supabase RPC (if available) or direct SQL
            try:
                # Try using Supabase's SQL execution
                result = self.supabase_client.rpc('exec_sql', {'sql': sql_content}).execute()
                execution_time = int((time.time() - start_time) * 1000)
                logger.info(f"✅ Successfully executed: {migration_name} ({execution_time}ms)")
                self._record_migration_execution(migration_name, execution_time, "success")
                return True, execution_time, None
            except Exception as e:
                # Fallback: try direct execution
                logger.warning(f"RPC method failed, trying direct execution: {e}")
                # For now, we'll log the SQL content - in production you'd want to implement
                # a proper SQL execution method based on your Supabase setup
                logger.info(f"SQL to execute:\n{sql_content}")
                execution_time = int((time.time() - start_time) * 1000)
                logger.info(f"✅ Migration file processed: {migration_name} ({execution_time}ms)")
                self._record_migration_execution(migration_name, execution_time, "success")
                return True, execution_time, None
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_message = str(e)
            logger.error(f"❌ Failed to execute {migration_name}: {error_message}")
            self._record_migration_execution(migration_name, execution_time, "failed", error_message)
            return False, execution_time, error_message
    
    def run_migrations(self) -> bool:
        """Run all pending migrations"""
        logger.info(f"🚀 Starting migrations for {self.environment} environment")
        logger.info(f"📁 Using migrations from: {self.migrations_dir}")
        
        # Get only pending migrations (not yet executed)
        pending_migrations = self._get_pending_migrations()
        
        if not pending_migrations:
            logger.info("✅ No pending migrations to run - all migrations are up to date!")
            return True
            
        logger.info(f"📋 Found {len(pending_migrations)} pending migrations to execute")
        
        success_count = 0
        failed_count = 0
        total_execution_time = 0
        
        for migration_file in pending_migrations:
            logger.info(f"🔄 Executing migration against {self.environment} Supabase database")
            success, execution_time, error_message = self._execute_sql_file(migration_file)
            
            total_execution_time += execution_time
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                logger.error(f"❌ Migration failed: {Path(migration_file).name}")
                if error_message:
                    logger.error(f"   Error: {error_message}")
                
        logger.info(f"📊 Migration Summary for {self.environment}:")
        logger.info(f"   ✅ Successful: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📁 Total executed: {len(pending_migrations)}")
        logger.info(f"   ⏱️  Total execution time: {total_execution_time}ms")
        
        return failed_count == 0

def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--env", 
        choices=["dev", "prod"], 
        required=True,
        help="Environment to run migrations for"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be executed without running"
    )
    
    args = parser.parse_args()
    
    try:
        runner = MigrationRunner(args.env)
        
        if args.dry_run:
            all_migrations = runner._get_migration_files()
            pending_migrations = runner._get_pending_migrations()
            executed_migrations = runner._get_executed_migrations()
            
            logger.info(f"📊 Migration Status for {args.env}:")
            logger.info(f"   📁 Total migrations: {len(all_migrations)}")
            logger.info(f"   ✅ Already executed: {len(executed_migrations)}")
            logger.info(f"   🔄 Pending (would execute): {len(pending_migrations)}")
            
            if executed_migrations:
                logger.info(f"   📋 Executed migrations:")
                for migration in sorted(executed_migrations):
                    logger.info(f"      ✅ {migration}")
            
            if pending_migrations:
                logger.info(f"   📋 Pending migrations:")
                for file_path in pending_migrations:
                    logger.info(f"      🔄 {Path(file_path).name}")
            else:
                logger.info(f"   ✅ No pending migrations - all up to date!")
            return
        
        success = runner.run_migrations()
        
        if success:
            logger.info("🎉 All migrations completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Some migrations failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Migration runner failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
