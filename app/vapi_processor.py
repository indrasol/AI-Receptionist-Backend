"""
VAPI Data Processor
Handles processing of VAPI API responses and updates database accordingly
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.database import get_supabase_client
from app.config.settings import VAPI_AUTH_TOKEN

logger = logging.getLogger(__name__)


def process_vapi_calls_response(vapi_response: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process VAPI API response and segregate calls by type
    
    Args:
        vapi_response: Raw response from VAPI API
        
    Returns:
        Dictionary with segregated calls and processing results
    """
    try:
        inbound_calls = []
        outbound_calls = []
        processed_count = 0
        errors = []
        
        for call in vapi_response:
            try:
                call_type = call.get("type", "")
                
                if call_type == "inboundPhoneCall":
                    inbound_calls.append(call)
                elif call_type == "outboundPhoneCall":
                    outbound_calls.append(call)
                else:
                    logger.warning(f"Unknown call type: {call_type} for call ID: {call.get('id')}")
                
                processed_count += 1
                
            except Exception as call_error:
                error_msg = f"Error processing call {call.get('id', 'unknown')}: {str(call_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Processed {processed_count} calls: {len(inbound_calls)} inbound, {len(outbound_calls)} outbound")
        
        return {
            "total_calls": processed_count,
            "inbound_calls": inbound_calls,
            "outbound_calls": outbound_calls,
            "errors": errors,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to process VAPI response: {str(e)}")
        return {
            "total_calls": 0,
            "inbound_calls": [],
            "outbound_calls": [],
            "errors": [f"Processing failed: {str(e)}"],
            "success": False
        }


async def update_inbound_calls_database(inbound_calls: List[Dict[str, Any]], organization_id: str) -> Dict[str, Any]:
    """
    Update inbound calls in the database
    
    Args:
        inbound_calls: List of inbound call data from VAPI
        organization_id: Organization ID to associate with calls
        
    Returns:
        Dictionary with update results
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_inbound_calls"
        
        updated_count = 0
        inserted_count = 0
        errors = []
        
        for call in inbound_calls:
            try:
                call_id = call.get("id")
                if not call_id:
                    continue
                
                # Check if call already exists
                existing_call = supabase.table(table_name).select("id").eq("vapi_call_id", call_id).execute()
                
                # Extract customer information
                customer = call.get("customer", {})
                customer_number = customer.get("number", "")
                
                # Prepare call data matching the actual table schema
                call_data = {
                    "vapi_call_id": call_id,
                    "organization_id": organization_id,
                    "phone_number": customer_number,  # Required field
                    "call_status": call.get("status", "unknown"),
                    "call_summary": call.get("summary", ""),
                    "call_recording_url": call.get("recordingUrl", ""),
                    "call_transcript": call.get("transcript", ""),
                    "success_evaluation": call.get("analysis", {}).get("successEvaluation", ""),
                    "call_type": call.get("type", "inboundPhoneCall"),
                    "call_duration_seconds": _calculate_call_duration(call),
                    "call_cost": call.get("cost", 0),
                    "ended_reason": call.get("endedReason", ""),
                    "customer_number": customer_number,
                    "phone_number_id": call.get("phoneNumberId", ""),
                    "updated_at": call.get("updatedAt", datetime.utcnow().isoformat()),
                    "created_at": call.get("createdAt", datetime.utcnow().isoformat()),
                    "first_name": customer.get("firstName", ""),
                    "last_name": customer.get("lastName", "")
                }
                

                
                if existing_call.data:
                    # Update existing call
                    result = supabase.table(table_name).update(call_data).eq("vapi_call_id", call_id).execute()
                    if result.data:
                        updated_count += 1
                        logger.info(f"Updated inbound call: {call_id}")
                    else:
                        errors.append(f"Failed to update inbound call: {call_id}")
                else:
                    # Insert new call
                    call_data["created_at"] = datetime.utcnow().isoformat()
                    
                    result = supabase.table(table_name).insert(call_data).execute()
                    if result.data:
                        inserted_count += 1
                        logger.info(f"Inserted new inbound call: {call_id}")
                    else:
                        errors.append(f"Failed to insert inbound call: {call_id}")
                        
            except Exception as call_error:
                error_msg = f"Error processing inbound call {call.get('id', 'unknown')}: {str(call_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Inbound calls processed: {updated_count} updated, {inserted_count} inserted")
        
        return {
            "updated_count": updated_count,
            "inserted_count": inserted_count,
            "errors": errors,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to update inbound calls database: {str(e)}")
        return {
            "updated_count": 0,
            "inserted_count": 0,
            "errors": [f"Database update failed: {str(e)}"],
            "success": False
        }


async def update_outbound_calls_database(outbound_calls: List[Dict[str, Any]], organization_id: str) -> Dict[str, Any]:
    """
    Update outbound calls in the database
    
    Args:
        outbound_calls: List of outbound call data from VAPI
        organization_id: Organization ID to associate with calls
        
    Returns:
        Dictionary with update results
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        updated_count = 0
        inserted_count = 0
        errors = []
        
        for call in outbound_calls:
            try:
                call_id = call.get("id")
                if not call_id:
                    continue
                
                # Extract customer information
                customer = call.get("customer", {})
                customer_number = customer.get("number", "")
                
                # Extract customer name if available, otherwise use NULL
                first_name = customer.get("firstName")  # Will be None if not present
                last_name = customer.get("lastName")    # Will be None if not present
                
                # Check if call already exists by vapi_call_id
                # This ensures we don't create duplicate records for the same VAPI call
                existing_call = supabase.table(table_name).select("id").eq("vapi_call_id", call_id).execute()
                
                # Prepare call data matching the actual leads table schema
                call_data = {
                    "organization_id": organization_id,  # Required field
                    "first_name": first_name,  # Required field
                    "last_name": last_name,    # Required field
                    "phone_number": customer_number,  # Required field
                    "source": "vapi_outbound",  # Required field
                    "imported_at": datetime.utcnow().isoformat(),  # Required field
                    "import_source": "vapi_outbound",  # Required field
                    "updated_at": call.get("updatedAt", datetime.utcnow().isoformat()),
                    "created_at": call.get("createdAt", datetime.utcnow().isoformat()),
                    "vapi_call_id": call_id,
                    "call_status": call.get("status", "unknown"),
                    "call_summary": call.get("summary", ""),
                    "call_recording_url": call.get("recordingUrl", ""),
                    "call_transcript": call.get("transcript", ""),
                    "success_evaluation": call.get("analysis", {}).get("successEvaluation", "")
                }
                
                if existing_call.data:
                    # Update existing call - only update fields that exist in the table
                    existing_record_id = existing_call.data[0]["id"]
                    update_fields = {
                        "organization_id": organization_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone_number": customer_number,
                        "source": "vapi_outbound",
                        "updated_at": call.get("updatedAt", datetime.utcnow().isoformat()),
                        "vapi_call_id": call_id,
                        "call_status": call.get("status", "unknown"),
                        "call_summary": call.get("summary", ""),
                        "call_recording_url": call.get("recordingUrl", ""),
                        "call_transcript": call.get("transcript", ""),
                        "success_evaluation": call.get("analysis", {}).get("successEvaluation", "")
                    }
                    
                    result = supabase.table(table_name).update(update_fields).eq("id", existing_record_id).execute()
                    if result.data:
                        updated_count += 1
                        logger.info(f"Updated outbound call {call_id} for phone: {customer_number}")
                    else:
                        errors.append(f"Failed to update outbound call {call_id} for phone: {customer_number}")
                else:
                    # Insert new call
                    
                    result = supabase.table(table_name).insert(call_data).execute()
                    if result.data:
                        inserted_count += 1
                        logger.info(f"Inserted new outbound call {call_id} for phone: {customer_number}")
                    else:
                        errors.append(f"Failed to insert outbound call {call_id} for phone: {customer_number}")
                        
            except Exception as call_error:
                error_msg = f"Error processing outbound call {call.get('id', 'unknown')}: {str(call_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Outbound calls processed: {updated_count} updated, {inserted_count} inserted")
        
        return {
            "updated_count": updated_count,
            "inserted_count": inserted_count,
            "errors": errors,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to update outbound calls database: {str(e)}")
        return {
            "updated_count": 0,
            "inserted_count": 0,
            "errors": [f"Database update failed: {str(e)}"],
            "success": False
        }


def _calculate_call_duration(call: Dict[str, Any]) -> Optional[float]:
    """
    Calculate call duration in seconds from start and end times
    
    Args:
        call: Call data from VAPI
        
    Returns:
        Duration in seconds or None if calculation fails
    """
    try:
        started_at = call.get("startedAt")
        ended_at = call.get("endedAt")
        
        if started_at and ended_at:
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds()
            return duration
        
        return None
        
    except Exception as e:
        logger.warning(f"Could not calculate call duration: {str(e)}")
        return None


async def process_and_update_vapi_calls(vapi_response: List[Dict[str, Any]], organization_id: str) -> Dict[str, Any]:
    """
    Main function to process VAPI calls and update database
    
    Args:
        vapi_response: Raw response from VAPI API
        organization_id: Organization ID to associate with calls
        
    Returns:
        Comprehensive results of the processing operation
    """
    try:
        logger.info(f"Starting VAPI calls processing for organization: {organization_id}")
        
        # Process and segregate calls
        processing_result = process_vapi_calls_response(vapi_response)
        
        if not processing_result["success"]:
            return processing_result
        
        # Update inbound calls
        inbound_result = await update_inbound_calls_database(
            processing_result["inbound_calls"], 
            organization_id
        )
        
        # Update outbound calls
        outbound_result = await update_outbound_calls_database(
            processing_result["outbound_calls"], 
            organization_id
        )
        
        # Compile final results
        total_updated = inbound_result["updated_count"] + outbound_result["updated_count"]
        total_inserted = inbound_result["inserted_count"] + outbound_result["inserted_count"]
        all_errors = processing_result["errors"] + inbound_result["errors"] + outbound_result["errors"]
        
        final_result = {
            "success": True,
            "total_calls_processed": processing_result["total_calls"],
            "inbound_calls": {
                "count": len(processing_result["inbound_calls"]),
                "updated": inbound_result["updated_count"],
                "inserted": inbound_result["inserted_count"]
            },
            "outbound_calls": {
                "count": len(processing_result["outbound_calls"]),
                "updated": outbound_result["updated_count"],
                "inserted": outbound_result["inserted_count"]
            },
            "summary": {
                "total_updated": total_updated,
                "total_inserted": total_inserted,
                "total_errors": len(all_errors)
            },
            "errors": all_errors
        }
        
        logger.info(f"VAPI calls processing completed successfully. "
                   f"Total: {total_updated + total_inserted} calls processed, "
                   f"{len(all_errors)} errors")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Failed to process and update VAPI calls: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "total_calls_processed": 0,
            "inbound_calls": {"count": 0, "updated": 0, "inserted": 0},
            "outbound_calls": {"count": 0, "updated": 0, "inserted": 0},
            "summary": {"total_updated": 0, "total_inserted": 0, "total_errors": 1},
            "errors": [f"Processing failed: {str(e)}"]
        } 