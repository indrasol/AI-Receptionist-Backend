#!/usr/bin/env python3
"""
Simple database connection test
Run this to check if your Supabase connection is working
"""

import sys
import os
sys.path.append('./app')
from config import settings
from supabase import create_client

def test_db_connection():
    """Test Supabase connection and table access"""
    
    print("🔍 Testing Database Connection...")
    print("=" * 50)
    
    # Get environment variables from settings
    supabase_url = settings.supabase_url
    supabase_key = settings.supabase_key
    table_name = settings.leads_table_name
    
    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key: {'*' * 20 if supabase_key else 'NOT SET'}")
    print(f"Table Name: {table_name}")
    print()
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return
    
    try:
        # Create client
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Test connection by getting table info
        print(f"🔍 Testing access to table: {table_name}")
        
        # Try to select from the table
        result = supabase.table(table_name).select("count", count="exact").execute()
        print(f"✅ Table access successful! Row count: {result.count}")
        
        # Try to get a few rows
        sample_result = supabase.table(table_name).select("*").limit(3).execute()
        print(f"✅ Sample data retrieved: {len(sample_result.data)} rows")
        
        if sample_result.data:
            print("📋 Sample data structure:")
            for key in sample_result.data[0].keys():
                print(f"   - {key}")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your .env file has correct SUPABASE_URL and SUPABASE_KEY")
        print("2. Verify your table name exists in Supabase")
        print("3. Check your Supabase API key has proper permissions")
        print("4. Make sure your table has RLS policies that allow access")

if __name__ == "__main__":
    test_db_connection() 