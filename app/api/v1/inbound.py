"""
Inbound Calls Management API
Handles all inbound call operations including retrieval and management
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from app.utils.auth import get_current_user
from app.database_operations import get_inbound_calls_by_user_organization
from typing import List, Dict, Any, Optional
import logging
import requests
from app.config.settings import DEBUG,VAPI_AUTH_TOKEN

from app.database import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Inbound Calls Management"])


@router.get("/get_calls", response_model=List[Dict[str, Any]])
async def get_inbound_calls(
    receptionist_id: Optional[str] = Query(None, description="Filter by receptionist"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all inbound calls for the current user's organization
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - List of inbound calls sorted by creation date (newest first)
    - Only shows calls from the user's organization
    
    **Response Format:**
    ```json
    [
        {
            "id": "uuid",
            "first_name": "John",
            "last_name": "Doe", 
            "phone_number": "+1234567890",
            "vapi_call_id": "call-123",
            "call_status": "ended",
            "call_summary": "Call summary...",
            "call_recording_url": "https://...",
            "call_transcript": "Full transcript...",
            "success_evaluation": "true",
            "call_type": "inboundPhoneCall",
            "call_duration_seconds": 120.5,
            "call_duration_formatted": "02:00",
            "call_cost": 0.0087,
            "ended_reason": "customer-ended-call",
            "customer_number": "+1234567890",
            "phone_number_id": "phone-123",
            "created_at": "2025-01-20T17:18:35.304Z",
            "updated_at": "2025-01-20T17:18:42.960Z",
            "call_date": "2025-01-20"
        }
    ]
    ```
    
    **Raises:**
    - 401: If user is not authenticated
    - 500: If organization not found or database error
    """
    try:
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=500, 
                detail="User organization not configured. Please contact administrator."
            )
        
        logger.info(f"Fetching inbound calls for organization: {user_organization.get('name', 'Unknown')}")
        
        supabase = get_supabase_client()

        # Query calls table directly
        query = supabase.table("ai_receptionist_inbound_calls").select("*")

        # If receptionist_id provided, translate to assistant_id
        if receptionist_id:
            rec_resp = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).execute()
            assistant_id = rec_resp.data[0]["assistant_id"] if rec_resp.data else None
            if assistant_id:
                query = query.eq("assistant_id", assistant_id)
            else:
                # No assistant found for this receptionist, return empty list early
                return []

        # --- NEW: sync latest calls from Vapi for this assistant (best-effort) ---
        if assistant_id:
            try:
                vapi_token = VAPI_AUTH_TOKEN
                if vapi_token:
                    vapi_resp = requests.get(
                        f"https://api.vapi.ai/call?assistantId={assistant_id}",
                        headers={"Authorization": f"Bearer {vapi_token}"}, timeout=15
                    )
                    if vapi_resp.status_code == 200:
                        from app.vapi_processor import process_and_update_vapi_calls
                        await process_and_update_vapi_calls(vapi_resp.json(), organization_id)
                else:
                    logger.warning("VAPI_AUTH_TOKEN not configured – skipping live sync")
            except Exception as sync_err:
                logger.warning(f"VAPI live sync failed: {sync_err}")

        # pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        result = query.order("created_at", desc=True).execute()

        inbound_calls = result.data or []
        
        if not inbound_calls:
            logger.info(f"No inbound calls found for organization: {user_organization.get('name')}")
            return []
        
        # Sort by created_at (newest first)
        sorted_calls = inbound_calls  # already ordered
        
        # Add call_date and call_duration_formatted fields to each call
        for call in sorted_calls:
            # Format call_date from created_at
            created_at = call.get("created_at")
            if created_at:
                try:
                    # Parse the ISO timestamp and format as YYYY-MM-DD
                    from datetime import datetime
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    call["call_date"] = dt.strftime("%Y-%m-%d")
                except Exception as date_error:
                    logger.warning(f"Could not format date for call {call.get('id')}: {str(date_error)}")
                    call["call_date"] = "Unknown"
            else:
                call["call_date"] = "Unknown"
            
            # Format call_duration_seconds to MM:SS format
            duration_seconds = call.get("call_duration_seconds")
            if duration_seconds and duration_seconds != "Unknown":
                try:
                    # Convert seconds to MM:SS format
                    total_seconds = float(duration_seconds)
                    minutes = int(total_seconds // 60)
                    seconds = int(total_seconds % 60)
                    call["call_duration_formatted"] = f"{minutes:02d}:{seconds:02d}"
                except (ValueError, TypeError) as duration_error:
                    logger.warning(f"Could not format duration for call {call.get('id')}: {str(duration_error)}")
                    call["call_duration_formatted"] = "Unknown"
            else:
                call["call_duration_formatted"] = "Unknown"
        
        logger.info(f"Retrieved {len(sorted_calls)} inbound calls for organization: {user_organization.get('name')}")
        
        return sorted_calls
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve inbound calls: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve inbound calls: {str(e)}"
        )


@router.post("/get_call", response_model=Dict[str, Any])
async def get_inbound_call_by_id(request: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """
    Get a specific inbound call by ID for the current user's organization
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Parameters:**
    - `call_id`: The ID of the inbound call to retrieve (path parameter)
    
    **Returns:**
    - Single inbound call details if found and belongs to user's organization
    
    **Response Format:**
    ```json
    {
        "id": "uuid",
        "first_name": "John",
        "last_name": "Doe", 
        "phone_number": "+1234567890",
        "vapi_call_id": "call-123",
        "call_status": "ended",
        "call_summary": "Call summary...",
        "call_recording_url": "https://...",
        "call_transcript": "Full transcript...",
        "success_evaluation": "true",
        "call_type": "inboundPhoneCall",
        "call_duration_seconds": 120.5,
        "call_cost": 0.0087,
        "ended_reason": "customer-ended-call",
        "customer_number": "+1234567890",
        "phone_number_id": "phone-123",
        "created_at": "2025-01-20T17:18:35.304Z",
        "updated_at": "2025-01-20T17:18:42.960Z"
    }
    ```
    
    **Raises:**
    - 401: If user is not authenticated
    - 403: If call doesn't belong to user's organization
    - 404: If call not found
    - 500: If organization not found or database error
    """
    try:
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=500, 
                detail="User organization not configured. Please contact administrator."
            )
        
        # Extract call_id from request body
        call_id = request.get("call_id")
        if not call_id:
            logger.error("No call_id provided in request body")
            raise HTTPException(
                status_code=400,
                detail="call_id is required in request body"
            )
        
        logger.info(f"Fetching inbound call {call_id} for organization: {user_organization.get('name', 'Unknown')}")
        
        # Get the specific inbound call and verify organization ownership
        from app.database_operations import get_inbound_call_by_id_and_org
        
        inbound_call = await get_inbound_call_by_id_and_org(call_id, organization_id)
        
        if not inbound_call:
            logger.warning(f"Inbound call {call_id} not found for organization: {user_organization.get('name')}")
            raise HTTPException(
                status_code=404,
                detail=f"Inbound call with ID {call_id} not found"
            )
        
        logger.info(f"Successfully retrieved inbound call {call_id} for organization: {user_organization.get('name')}")
        
        return inbound_call
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        call_id = request.get("call_id", "unknown")
        logger.error(f"Failed to retrieve inbound call {call_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve inbound call: {str(e)}"
        ) 


@router.post("/vapi/sync_calls")
async def sync_vapi_calls(current_user: dict = Depends(get_current_user)):
    """
    Call VAPI API to get latest calls, process the response, and update database
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - Database update results
    - VAPI response data
    
    **What it does:**
    1. Calls VAPI API to get latest calls
    2. Processes and segregates calls by type (inbound/outbound)
    3. Updates database (inserts new, updates existing)
    4. Returns comprehensive results
    """
    try:
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=500, 
                detail="User organization not configured. Please contact administrator."
            )
        
        # Call VAPI API to get latest calls
        vapi_token = VAPI_AUTH_TOKEN
        if not vapi_token:
            logger.error("VAPI auth token not configured")
            raise HTTPException(
                status_code=500,
                detail="VAPI authentication token not configured"
            )
        
        vapi_url = "https://api.vapi.ai/call"
        headers = {
            "Authorization": f"Bearer {vapi_token}"
        }
        
        logger.info(f"Calling VAPI API: {vapi_url}")
        
        response = requests.get(vapi_url, headers=headers)
        
        if response.status_code != 200:
            error_message = f"VAPI API returned status {response.status_code}"
            try:
                error_data = response.json()
                error_message += f": {error_data}"
            except:
                error_message += f": {response.text}"
            
            logger.error(error_message)
            raise HTTPException(
                status_code=response.status_code,
                detail=f"VAPI API error: {error_message}"
            )
        
        vapi_response_data = response.json()
        logger.info(f"VAPI API Response: {len(vapi_response_data)} calls received")
        
        # Print to console
        print("=" * 50)
        print("VAPI API CALLS LIST:")
        print("=" * 50)
        print(f"Status Code: {response.status_code}")
        print(f"Total Calls: {len(vapi_response_data)}")
        print("=" * 50)
        
        # Process and update database
        try:
            from app.vapi_processor import process_and_update_vapi_calls
            
            logger.info(f"Processing VAPI calls for organization: {organization_id}")
            processing_result = await process_and_update_vapi_calls(vapi_response_data, organization_id)
            
            if processing_result["success"]:
                logger.info("Successfully processed and updated VAPI calls in database")
                
                # Print processing results to console
                print("=" * 50)
                print("DATABASE UPDATE RESULTS:")
                print("=" * 50)
                print(f"Total calls processed: {processing_result['total_calls_processed']}")
                print(f"Inbound calls: {processing_result['inbound_calls']['count']} found, "
                      f"{processing_result['inbound_calls']['updated']} updated, "
                      f"{processing_result['inbound_calls']['inserted']} inserted")
                print(f"Outbound calls: {processing_result['outbound_calls']['count']} found, "
                      f"{processing_result['outbound_calls']['updated']} updated, "
                      f"{processing_result['outbound_calls']['inserted']} inserted")
                print(f"Total updated: {processing_result['summary']['total_updated']}")
                print(f"Total inserted: {processing_result['summary']['total_inserted']}")
                print(f"Errors: {processing_result['summary']['total_errors']}")
                if processing_result['errors']:
                    print("Error details:")
                    for error in processing_result['errors']:
                        print(f"  - {error}")
                print("=" * 50)
                
                return {
                    "message": "VAPI API sync successful and database updated",
                    "vapi_response": vapi_response_data,
                    "database_update": processing_result
                }
                    
            else:
                logger.error(f"Failed to process VAPI calls: {processing_result.get('error', 'Unknown error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process VAPI calls: {processing_result.get('error', 'Unknown error')}"
                )
                
        except Exception as processing_error:
            logger.error(f"Error processing VAPI calls: {str(processing_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {str(processing_error)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"VAPI API request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to call VAPI API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


from typing import List


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    receptionist_ids: Optional[List[str]] = Query(None, description="List of receptionist IDs to include"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get dashboard statistics for the current user's organization
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - Dashboard metrics (inbound/outbound calls, success rates, trends)
    - Data comes from SQL views (dev tables in debug mode, production tables otherwise)
    
    **What it returns:**
    - Inbound calls: total, today, yesterday, last 14 days
    - Outbound calls: total, today, yesterday, last 14 days
    - Success rates and change percentages
    - 14-day trend data for charts
    """
    try:
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=500, 
                detail="User organization not configured. Please contact administrator."
            )
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Use production dashboard views
        dashboard_view = "ai_receptionist_dashboard_view"
        trends_view = "ai_receptionist_daily_trends_view"
        logger.info("Using dashboard views")
        
        # Build base query on new receptionist-centric view
        query = supabase.table(dashboard_view).select("*")

        if receptionist_ids:
            query = query.in_("receptionist_id", receptionist_ids)
        else:
            # Default: all receptionists within org -> get their ids first
            rec_rows = supabase.table("receptionists").select("id").eq("org_id", organization_id).execute()
            rec_ids = [r["id"] for r in (rec_rows.data or [])]
            if rec_ids:
                query = query.in_("receptionist_id", rec_ids)
            else:
                # no receptionists yet
                return {"dashboard": {}, "trends": [], "message": "No receptionists"}

        dashboard_result = query.execute()
        
        if not dashboard_result.data:
            logger.warning(f"No dashboard data found for organization {organization_id}")
            # Return empty dashboard with zeros
            return {
                "dashboard": {
                    "inbound_calls_total": 0,
                    "inbound_calls_today": 0,
                    "inbound_calls_yesterday": 0,
                    "inbound_calls_last_14_days": 0,
                    "outbound_calls_total": 0,
                    "outbound_calls_today": 0,
                    "outbound_calls_yesterday": 0,
                    "outbound_calls_last_14_days": 0,
                    "outbound_success_rate": 0.0,
                    "inbound_calls_change_percent": 0.0,
                    "outbound_calls_change_percent": 0.0,
                    "success_rate_change_percent": 0.0,
                    "outbound_calls_successful": 0,
                    "outbound_calls_completed": 0
                },
                "trends": [],
                "message": "No data available for dashboard"
            }
        
        dashboard_data = dashboard_result.data[0]
        
        # Daily trends filtered by receptionist IDs
        trends_query = supabase.table(trends_view).select("*")
        if receptionist_ids:
            trends_query = trends_query.in_("receptionist_id", receptionist_ids)
        else:
            trends_query = trends_query.in_("receptionist_id", rec_ids)

        trends_result = trends_query.order("date").execute()
        trends_data = trends_result.data if trends_result.data else []
        
        # Format the response
        dashboard_stats = {
            "dashboard": {
                "inbound_calls_total": dashboard_data.get("inbound_calls_total", 0),
                "inbound_calls_today": dashboard_data.get("inbound_calls_today", 0),
                "inbound_calls_yesterday": dashboard_data.get("inbound_calls_yesterday", 0),
                "inbound_calls_last_14_days": dashboard_data.get("inbound_calls_last_14_days", 0),
                "outbound_calls_total": dashboard_data.get("outbound_calls_total", 0),
                "outbound_calls_today": dashboard_data.get("outbound_calls_today", 0),
                "outbound_calls_yesterday": dashboard_data.get("outbound_calls_yesterday", 0),
                "outbound_calls_last_14_days": dashboard_data.get("outbound_calls_last_14_days", 0),
                "outbound_success_rate": dashboard_data.get("outbound_success_rate", 0.0),
                "inbound_calls_change_percent": dashboard_data.get("inbound_calls_change_percent", 0.0),
                "outbound_calls_change_percent": dashboard_data.get("outbound_calls_change_percent", 0.0),
                "success_rate_change_percent": dashboard_data.get("success_rate_change_percent", 0.0),
                "outbound_calls_successful": dashboard_data.get("outbound_calls_successful", 0),
                "outbound_calls_completed": dashboard_data.get("outbound_calls_completed", 0)
            },
            "trends": trends_data,
            "receptionist": {
                "id": dashboard_data.get("receptionist_id"),
                "name": dashboard_data.get("receptionist_name", "Receptionist")
            },
            "metadata": {
                "current_date": dashboard_data.get("current_date"),
                "yesterday_date": dashboard_data.get("yesterday_date"),
                "fourteen_days_ago_date": dashboard_data.get("fourteen_days_ago_date"),
                "environment": "development" if DEBUG else "production"
            }
        }
        
        logger.info(f"Successfully retrieved dashboard stats for organization {organization_id}")
        
        return dashboard_stats
        
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )


 