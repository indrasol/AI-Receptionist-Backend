"""
Database operations for AI Receptionist API
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.database import get_supabase_client
from app.config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)

async def save_inbound_call_data(call_data: Dict[str, Any], organization_id: str) -> Optional[Dict[str, Any]]:
    """
    Save inbound call data to ai_receptionist_inbound_calls table
    
    Args:
        call_data: Call data from VAPI webhook
        organization_id: Organization ID to associate with the call
        
    Returns:
        Saved call record or None if failed
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_inbound_calls"
        
        # Extract data from call_data
        inbound_call_record = {
            "phone_number": call_data.get("customer_number", ""),
            "organization_id": organization_id,
            "vapi_call_id": call_data.get("vapi_call_id"),
            "call_status": call_data.get("call_status", "completed"),
            "call_summary": call_data.get("call_summary"),
            "call_recording_url": call_data.get("call_recording_url"),
            "call_transcript": call_data.get("call_transcript"),
            "success_evaluation": call_data.get("success_evaluation"),
            "call_type": call_data.get("call_type", "inboundPhoneCall"),
            "call_duration_seconds": call_data.get("call_duration_seconds"),
            "call_cost": call_data.get("call_cost"),
            "ended_reason": call_data.get("ended_reason"),
            "customer_number": call_data.get("customer_number"),
            "phone_number_id": call_data.get("phone_number_id"),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert the record
        result = supabase.table(table_name).insert(inbound_call_record).execute()
        
        if result.data:
            logger.info(f"Successfully saved inbound call data for call ID: {call_data.get('vapi_call_id')} to {table_name}")
            return result.data[0]
        else:
            logger.warning("No data returned when saving inbound call")
            return None
            
    except Exception as e:
        logger.error(f"Failed to save inbound call data: {str(e)}")
        return None

async def update_outbound_call_data(call_data: Dict[str, Any], organization_id: str) -> Optional[Dict[str, Any]]:
    """
    Update outbound call data in ai_receptionist_leads table
    
    Args:
        call_data: Call data from VAPI webhook
        organization_id: Organization ID to associate with the call
        
    Returns:
        Updated lead record or None if failed
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        # Extract data from call_data
        update_data = {
            "call_status": call_data.get("call_status", "ended"),
            "call_summary": call_data.get("call_summary"),
            "call_recording_url": call_data.get("call_recording_url"),
            "call_transcript": call_data.get("call_transcript"),
            "success_evaluation": call_data.get("success_evaluation"),
            "organization_id": organization_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Find lead by vapi_call_id and update
        vapi_call_id = call_data.get("vapi_call_id")
        if vapi_call_id:
            result = supabase.table(table_name).update(update_data).eq("vapi_call_id", vapi_call_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated outbound call data for VAPI call ID: {vapi_call_id}")
                return result.data[0]
            else:
                logger.warning(f"No lead found with VAPI call ID: {vapi_call_id}")
                return None
        else:
            logger.warning("No VAPI call ID found in call data")
            return None
            
    except Exception as e:
        logger.error(f"Failed to update outbound call data: {str(e)}")
        return None

async def get_organization_id_by_name(org_name: str) -> Optional[str]:
    """
    Get organization ID by name
    
    Args:
        org_name: Organization name (e.g., 'CSA')
        
    Returns:
        Organization ID or None if not found
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("organizations").select("id").eq("name", org_name).execute()
        
        if result.data:
            return result.data[0]["id"]
        else:
            logger.warning(f"Organization not found: {org_name}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get organization ID: {str(e)}")
        return None


async def get_organization_by_vapi_org_id(vapi_org_id: str) -> Optional[Dict[str, Any]]:
    """
    Get organization by VAPI organization ID
    
    Args:
        vapi_org_id: VAPI organization ID
        
    Returns:
        Organization info or None if not found
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("organizations").select("*").eq("vapi_org_id", vapi_org_id).execute()
        
        if result.data:
            return result.data[0]
        else:
            logger.warning(f"Organization not found with VAPI org ID: {vapi_org_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get organization by VAPI org ID: {str(e)}")
        return None

async def get_calls_by_organization(organization_id: str, call_type: str = None) -> list:
    """
    Get calls for a specific organization
    
    Args:
        organization_id: Organization ID
        call_type: Optional filter by call type ('inbound' or 'outbound')
        
    Returns:
        List of calls
    """
    try:
        supabase = get_supabase_client()
        
        if call_type == "inbound":
            # Get inbound calls
            table_name = "ai_receptionist_inbound_calls"
            result = supabase.table(table_name).select("*").eq("organization_id", organization_id).order("created_at", desc=True).execute()
        elif call_type == "outbound":
            # Get outbound calls (leads)
            table_name = "ai_receptionist_leads"
            result = supabase.table(table_name).select("*").eq("organization_id", organization_id).order("created_at", desc=True).execute()
        else:
            # Get all calls
            inbound_table_name = "ai_receptionist_inbound_calls"
            inbound_result = supabase.table(inbound_table_name).select("*").eq("organization_id", organization_id).execute()
            outbound_result = supabase.table("ai_receptionist_leads").select("*").eq("organization_id", organization_id).execute()
            
            # Combine and sort by created_at
            all_calls = []
            if inbound_result.data:
                for call in inbound_result.data:
                    call["call_type"] = "inbound"
                    all_calls.append(call)
                    
            if outbound_result.data:
                for call in outbound_result.data:
                    call["call_type"] = "outbound"
                    all_calls.append(call)
            
            # Sort by created_at
            all_calls.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return all_calls
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"Failed to get calls by organization: {str(e)}")
        return []


async def get_default_organization() -> Optional[Dict[str, Any]]:
    """
    Get the default CSA organization
    
    Returns:
        CSA organization info or None if not found
    """
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("organizations").select("*").eq("name", "CSA").execute()
        
        if result.data:
            return {
                "id": result.data[0]["id"],
                "name": "CSA",
                "description": result.data[0].get("description", ""),
                "role": "member"
            }
        else:
            logger.error("Default CSA organization not found in database")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get default organization: {str(e)}")
        return None


async def get_user_organization_from_claims(user_claims: dict) -> Optional[Dict[str, Any]]:
    """
    Get user's organization information from JWT claims (most efficient method)
    
    Args:
        user_claims: User claims from JWT token
        
    Returns:
        Organization info or None if not found
    """
    try:
        # Check if organization info is already in JWT claims
        org_id = user_claims.get("organization_id")
        org_name = user_claims.get("organization_name")
        print(f"org_id12334: {org_id}")
        if org_id:
            # Get organization details from database
            supabase = get_supabase_client()
            org_result = supabase.table("organizations").select("*").eq("id", org_id).execute()
            
            if org_result.data:
                db_name = org_result.data[0]["name"]
                print(f"db_name12334: {db_name}")
                logger.info(f"Found organization {db_name} for user from JWT claims")
                return {
                    "id": org_id,
                    "name": db_name,
                    "description": org_result.data[0].get("description", ""),
                    "role": "member"
                }
        
        # If no organization in claims, return None to trigger fallback
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user organization from claims: {str(e)}")
        return None


async def get_user_organization(user_id: str, user_claims: dict = None) -> Optional[Dict[str, Any]]:
    """
    Get user's organization information from Supabase Auth user metadata
    
    Args:
        user_id: User ID from JWT token (auth.users.id)
        user_claims: Optional JWT claims (more efficient if available)
        
    Returns:
        Organization info or None if not found
    """
    try:
        supabase = get_supabase_client()
        print(f"user_id12334*********++++++: {user_id}")
        query_col = "user_id" if "@" not in user_id else "email"
        prof_resp = (
            supabase.table("profiles")
            .select("organization_id, organizations(name, description)")
            .eq(query_col, user_id)
            .single()
            .execute()
        )
        print(f"prof_resp12334*********: {prof_resp}")
        logger.debug(f"Profile org lookup response: {prof_resp}")

        if prof_resp.data and prof_resp.data.get("organization_id"):
            org_id_row = prof_resp.data["organization_id"]
            org_obj = prof_resp.data.get("organizations") or {}
            return {
                "id": org_id_row,
                "name": org_obj.get("name", "Organization"),
                "description": org_obj.get("description", ""),
                "role": "member",
            }

        logger.warning(f"No organization linked to user {user_id} in profiles table")
        return None

    except Exception as e:
        logger.error(f"Failed to get user organization: {str(e)}")
        return None


async def get_calls_by_user_organization(user_id: str, call_type: str = None, user_claims: dict = None) -> list:
    """
    Get calls for a user's organization
    
    Args:
        user_id: User ID from Supabase Auth
        call_type: Optional filter by call type
        user_claims: Optional JWT claims for efficient organization lookup
        
    Returns:
        List of calls
    """
    try:
        # First get user's organization
        user_org = await get_user_organization(user_id, user_claims)
        if not user_org:
            return []
        
        organization_id = user_org["id"]
        
        # Then get calls for that organization
        return await get_calls_by_organization(organization_id, call_type)
        
    except Exception as e:
        logger.error(f"Failed to get calls by user organization: {str(e)}")
        return []


async def get_inbound_calls_by_user_organization(user_id: str, user_claims: dict = None) -> list:
    """
    Get inbound calls for a user's organization
    
    Args:
        user_id: User ID from Supabase Auth
        user_claims: Optional JWT claims for efficient organization lookup
        
    Returns:
        List of inbound calls
    """
    try:
        # First get user's organization
        user_org = await get_user_organization(user_id, user_claims)
        if not user_org:
            return []
        
        organization_id = user_org["id"]
        
        # Get inbound calls for that organization
        supabase = get_supabase_client()
        table_name = "ai_receptionist_inbound_calls"
        
        result = supabase.table(table_name).select("*").eq("organization_id", organization_id).order("created_at", desc=True).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logger.error(f"Failed to get inbound calls by user organization: {str(e)}")
        return []


async def get_inbound_call_by_id_and_org(call_id: str, organization_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific inbound call by ID and verify it belongs to the organization
    
    Args:
        call_id: Inbound call ID to retrieve
        organization_id: Organization ID to verify ownership
        
    Returns:
        Inbound call data or None if not found
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_inbound_calls"
        
        # Get the specific call and verify organization ownership
        result = supabase.table(table_name).select("*").eq("id", call_id).eq("organization_id", organization_id).execute()
        
        if result.data:
            logger.info(f"Found inbound call {call_id} for organization {organization_id}")
            return result.data[0]
        else:
            logger.warning(f"Inbound call {call_id} not found or doesn't belong to organization {organization_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get inbound call by ID: {str(e)}")
        return None


async def ensure_user_organization(user_id: str) -> str:
    """
    Ensure user has CSA organization in their metadata
    
    Args:
        user_id: User ID from Supabase Auth
        
    Returns:
        Organization ID
    """
    try:
        # Get CSA organization ID first
        supabase = get_supabase_client()
        org_result = supabase.table("organizations").select("id").eq("name", "CSA").execute()
        if not org_result.data:
            logger.error("CSA organization not found in database")
            return None
        
        organization_id = org_result.data[0]["id"]
        
        # Try to update user metadata if service role key is available
        if SUPABASE_SERVICE_ROLE_KEY:
            try:
                from app.database import get_supabase_admin_client
                supabase_admin = get_supabase_admin_client()
                
                # Update user metadata to include organization
                result = supabase_admin.auth.admin.update_user_by_id(user_id, {
                    "user_metadata": {
                        "organization_id": organization_id,
                        "organization_name": "CSA"
                    }
                })
                
                if result:
                    logger.info(f"Updated user {user_id} metadata with CSA organization")
                else:
                    logger.warning(f"Failed to update user {user_id} metadata")
                    
            except Exception as admin_error:
                logger.warning(f"Admin update failed for user {user_id}: {str(admin_error)}")
                # Continue without admin update
        
        logger.info(f"User {user_id} will use CSA organization: {organization_id}")
        return organization_id
        
    except Exception as e:
        logger.error(f"Failed to ensure user organization: {str(e)}")
        return None 