#!/usr/bin/env python3
"""
Migration script to update existing Supabase users with organization metadata.
This script adds organization_id and organization_name to user_metadata for all existing users.

Usage:
    python3 scripts/update_user_organizations.py

Requirements:
    - AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY environment variable must be set
    - AI_RECEPTION_SUPABASE_URL environment variable must be set
"""

import os
import asyncio
from supabase import create_client, Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_user_organizations():
    """Update all existing users with CSA organization metadata"""
    
    # Get environment variables
    supabase_url = os.getenv('AI_RECEPTION_SUPABASE_URL')
    service_role_key = os.getenv('AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url:
        logger.error("AI_RECEPTION_SUPABASE_URL environment variable not set")
        return False
    
    if not service_role_key:
        logger.error("AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY environment variable not set")
        return False
    
    try:
        # Create Supabase client with service role key (admin access)
        supabase: Client = create_client(supabase_url, service_role_key)
        logger.info("Connected to Supabase with service role key")
        
        # CSA organization ID (hardcoded as per schema)
        csa_org_id = "550e8400-e29b-41d4-a716-446655440000"
        csa_org_name = "CSA"
        
        # Get all users
        logger.info("Fetching all users...")
        users_result = supabase.auth.admin.list_users()
        
        if not users_result:
            logger.warning("No users found")
            return True
        
        logger.info(f"Found {len(users_result)} users")
        
        # Update each user's metadata
        updated_count = 0
        for user in users_result:
            try:
                user_id = user.id
                current_metadata = user.user_metadata or {}
                
                # Check if user already has organization info
                if current_metadata.get('organization_id') == csa_org_id:
                    logger.info(f"User {user.email or 'unknown'} already has CSA organization")
                    continue
                
                # Update user metadata with organization info
                new_metadata = {
                    **current_metadata,
                    'organization_id': csa_org_id,
                    'organization_name': csa_org_name
                }
                
                # Update the user
                result = supabase.auth.admin.update_user_by_id(
                    user_id,
                    user_metadata=new_metadata
                )
                
                if result:
                    logger.info(f"Updated user {user.email or 'unknown'} with CSA organization")
                    updated_count += 1
                else:
                    logger.warning(f"Failed to update user {user.email or 'unknown'}")
                    
            except Exception as user_error:
                logger.error(f"Error updating user {user.email or 'unknown'}: {str(user_error)}")
                continue
        
        logger.info(f"Migration completed. Updated {updated_count} users with CSA organization.")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

async def main():
    """Main function"""
    logger.info("Starting user organization migration...")
    
    success = await update_user_organizations()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 