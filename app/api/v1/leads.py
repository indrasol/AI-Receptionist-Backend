from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Header, Query
from app.schemas.lead import Lead, LeadResponse, LeadList, LeadDB, GoogleSheetsResponse, LeadIdRequest, CallLeadResponse, CallLeadsRequest, CallLeadsResponse, VapiVoiceIdResponse, VapiBackendVoiceResponse
from app.utils.auth import get_current_user
import logging
import pandas as pd
import io
import requests
import re
import os
from datetime import datetime
from app.database import get_supabase_client
from app.config.settings import VAPI_WEBHOOK_SECRET
from typing import List, Tuple, Dict, Any, Optional
from pydantic import BaseModel
import httpx
import os

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Outbound Management"])


async def insert_leads_to_database(valid_rows: List[dict], source: str, source_info: str = None, current_user: dict = None) -> List[dict]:
    """
    Insert validated leads into database
    
    Args:
        valid_rows: List of validated lead data
        source: Source of the leads (e.g., 'google_sheets', 'csv_upload')
        source_info: Additional source information (e.g., URL, filename)
        current_user: Authenticated user information for tracking
        
    Returns:
        List of complete database records with IDs and metadata
        
    Raises:
        HTTPException: If database insertion fails
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        # Prepare data for insertion (map to database column names)
        db_rows = []
        for row in valid_rows:
            # Format phone number with + prefix if not present
            phone_number = row["PhoneNumber"]
            formatted_phone = phone_number
            if phone_number and not formatted_phone.startswith('+'):
                formatted_phone = f"+{formatted_phone}"
            
            db_row = {
                "first_name": row["FirstName"],
                "last_name": row["LastName"],
                "phone_number": formatted_phone,
                "source": source
            }
            
            # Add source-specific information
            if source_info:
                if source == "google_sheets":
                    db_row["sheet_url"] = source_info
                elif source == "csv_upload":
                    db_row["filename"] = source_info
            
            # Add import metadata
            db_row["imported_at"] = datetime.utcnow().isoformat()
            db_row["import_source"] = source
            
            # Add user tracking information
            if current_user:
                db_row["created_by_user_id"] = current_user.get("sub")
                db_row["created_by_user_email"] = current_user.get("email")
                # Add organization_id from user's organization
                user_organization = current_user.get("organization", {})
                if user_organization.get("id"):
                    db_row["organization_id"] = user_organization.get("id")
            
            db_rows.append(db_row)
        
        # Insert all valid rows
        result = supabase.table(table_name).insert(db_rows).execute()
        
        if not result.data:
            logger.warning("No data returned from database insertion")
            return []
        
        # Map database records back to original format for consistency
        mapped_records = []
        for record in result.data:
            # Ensure phone number is formatted with + prefix
            phone_number = record.get("phone_number", "")
            formatted_phone = phone_number
            if phone_number and not formatted_phone.startswith('+'):
                formatted_phone = f"+{formatted_phone}"
            
            mapped_record = {
                "FirstName": record.get("first_name", ""),
                "LastName": record.get("last_name", ""),
                "PhoneNumber": formatted_phone,
                "id": record.get("id"),
                "source": record.get("source"),
                "imported_at": record.get("imported_at"),
                "created_at": record.get("created_at"),
                "created_by_user_id": record.get("created_by_user_id"),
                "created_by_user_email": record.get("created_by_user_email"),
                "vapi_call_id": record.get("vapi_call_id"),
                "call_status": record.get("call_status"),
                "call_summary": record.get("call_summary"),
                "call_recording_url": record.get("call_recording_url"),
                "call_transcript": record.get("call_transcript"),
                "success_evaluation": record.get("success_evaluation")
            }
            
            # Add source-specific fields
            if source == "google_sheets" and record.get("sheet_url"):
                mapped_record["sheet_url"] = record.get("sheet_url")
            elif source == "csv_upload" and record.get("filename"):
                mapped_record["filename"] = record.get("filename")
            
            mapped_records.append(mapped_record)
        
        logger.info(f"Successfully inserted {len(mapped_records)} leads into database from {source}")
        return mapped_records  # Return mapped records in consistent format
        
    except Exception as db_error:
        logger.error(f"Database insertion failed: {str(db_error)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save leads to database: {str(db_error)}"
        )


def validate_sheet_data(df: pd.DataFrame) -> Tuple[List[dict], List[str]]:
    """
    Common validation function for sheet data (CSV or Google Sheets)
    
    Args:
        df: Pandas DataFrame containing the sheet data
        
    Returns:
        Tuple of (valid_rows, invalid_rows)
        
    Raises:
        HTTPException: If column structure is invalid
    """
    # Expected column names (case-sensitive)
    expected_columns = ['FirstName', 'LastName', 'PhoneNumber']
    
    # Check if we have exactly 3 columns
    if len(df.columns) != 3:
        error_msg = f"Sheet must have exactly 3 columns. Found {len(df.columns)} columns: {list(df.columns)}"
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check if all expected columns are present
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        error_msg = f"Missing required columns: {missing_columns}. Sheet must have: {expected_columns}"
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check if there are any extra columns
    extra_columns = [col for col in df.columns if col not in expected_columns]
    if extra_columns:
        error_msg = f"Unexpected columns found: {extra_columns}. Sheet must only have: {expected_columns}"
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Validate data in each row
    valid_rows = []
    invalid_rows = []
    
    for index, row in df.iterrows():
        row_num = index + 1  # Convert to 1-based indexing for user-friendly messages
        
        # Check if required fields are not empty
        first_name = str(row['FirstName']).strip() if pd.notna(row['FirstName']) else ""
        last_name = str(row['LastName']).strip() if pd.notna(row['LastName']) else ""
        phone_number = str(row['PhoneNumber']).strip() if pd.notna(row['PhoneNumber']) else ""
        
        # Skip header row if it's duplicated
        if first_name.lower() == 'firstname' and last_name.lower() == 'lastname' and phone_number.lower() == 'phonenumber':
            continue
        
        # Skip completely empty rows
        if not first_name and not last_name and not phone_number:
            continue
        
        # Validate required fields (LastName is optional)
        if not first_name:
            invalid_rows.append(f"Row {row_num}: FirstName is empty")
            continue
            
        if not phone_number:
            invalid_rows.append(f"Row {row_num}: PhoneNumber is empty")
            continue
        
        # Validate phone number format (basic check)
        if len(phone_number) < 7:
            invalid_rows.append(f"Row {row_num}: PhoneNumber too short - {phone_number}")
            continue
        
        # If all validations pass, add to valid rows
        valid_rows.append({
            "FirstName": first_name,
            "LastName": last_name,
            "PhoneNumber": phone_number
        })
    
    return valid_rows, invalid_rows


@router.post("/upload_url", response_model=GoogleSheetsResponse)
async def upload_url(
    sheets_url: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Read Google Sheets content from URL and validate format
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Parameters:**
    - `sheets_url`: Google Sheets URL to process
    
    **Returns:**
    - Processed and validated leads data with database IDs

    Example Response:

    {
    "message": "Google Sheets content processed and saved successfully. Found 1 valid rows.",
    "rows_count": 1,
    "columns": [
        "FirstName",
        "LastName",
        "PhoneNumber"
    ],
    "data": [
        {
            "FirstName": "Kanoj",
            "LastName": "g",
            "PhoneNumber": "+19132956186",
            "id": 17,
            "source": "google_sheets",
            "imported_at": "2025-08-14T19:47:27.821051+00:00",
            "created_at": "2025-08-14T19:47:28.428299+00:00",
            "created_by_user_id": "5839308a-f881-4809-bbaa-0f9fcdea7107",
            "created_by_user_email": "kanoj2108@gmail.com",
            "vapi_call_id": null,
            "call_status": "pending",
            "call_summary": null,
            "call_recording_url": null,
            "call_transcript": null,
            "success_evaluation": null,
            "sheet_url": "https://docs.google.com/spreadsheets/d/1xP1MSODD9VRpjQD6Pt-QW_QXdU6qmmrK5cyl_MN0JZM/edit?usp=sharing"
        }
    ]
}
    """
    
    try:
        # Extract Google Sheets ID from URL
        # Pattern: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
        sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheets_url)
        
        if not sheet_id_match:
            raise HTTPException(
                status_code=400, 
                detail="Invalid Google Sheets URL. Please provide a valid Google Sheets URL."
            )
        
        sheet_id = sheet_id_match.group(1)
        
        # Convert to CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Download the CSV content
        response = requests.get(csv_url)
        response.raise_for_status()
        
        # Read CSV content
        csv_content = response.text
        
        # Parse with pandas
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Use common validation function
        valid_rows, invalid_rows = validate_sheet_data(df)
        
        # Return only valid rows, with info about invalid ones
        if not valid_rows:
            raise HTTPException(
                status_code=400, 
                detail=f"No valid rows found. All rows failed validation: {'; '.join(invalid_rows)}"
            )
        
        # Insert valid rows into database
        db_records = await insert_leads_to_database(valid_rows, "google_sheets", sheets_url, current_user)
        
        # Log user action
        logger.info(f"User {current_user.get('email', 'unknown')} uploaded {len(valid_rows)} leads from Google Sheets")
        
        # Return success response with database records
        message = f"Google Sheets content processed and saved successfully. Found {len(valid_rows)} valid rows."
        if invalid_rows:
            message += f" Skipped {len(invalid_rows)} invalid rows: {', '.join(invalid_rows[:3])}"
            if len(invalid_rows) > 3:
                message += f" and {len(invalid_rows) - 3} more"
        
        return GoogleSheetsResponse(
            message=message,
            rows_count=len(valid_rows),
            columns=['FirstName', 'LastName', 'PhoneNumber'],
            data=db_records  # Use database records directly
        )
        
    except requests.RequestException as e:
        error_msg = f"Failed to download Google Sheets: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
        
    except Exception as e:
        error_msg = f"Failed to process Google Sheets: {str(e)}"
        logger.error(f"Google Sheets processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/upload_excel", response_model=GoogleSheetsResponse)
async def upload_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload CSV file and validate format (FirstName, LastName, PhoneNumber)
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Parameters:**
    - `file`: CSV file with columns: FirstName, LastName, PhoneNumber
    
    **Returns:**
    - Processed and validated leads data with database IDs

    Example Response:
    Same as upload_url
    """
    # Validate file type - now accepts CSV files
    if not file.filename.endswith(('.csv')):
        raise HTTPException(status_code=400, detail="File must be a CSV file (.csv)")
    
    try:
        # Read CSV file
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse with pandas
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Use common validation function
        valid_rows, invalid_rows = validate_sheet_data(df)
        
        # Return only valid rows, with info about invalid ones
        if not valid_rows:
            raise HTTPException(
                status_code=400, 
                detail=f"No valid rows found. All rows failed validation: {'; '.join(invalid_rows)}"
            )
        
        # Insert valid rows into database
        db_records = await insert_leads_to_database(valid_rows, "csv_upload", file.filename, current_user)
        
        # Log user action
        logger.info(f"User {current_user.get('email', 'unknown')} uploaded {len(valid_rows)} leads from CSV file: {file.filename}")
        
        # Return success response with database records
        message = f"CSV file processed and saved successfully. Found {len(valid_rows)} valid rows."
        if invalid_rows:
            message += f" Skipped {len(invalid_rows)} invalid rows: {', '.join(invalid_rows[:3])}"
            if len(invalid_rows) > 3:
                message += f" and {len(invalid_rows) - 3} more"
        
        return GoogleSheetsResponse(
            message=message,
            rows_count=len(valid_rows),
            columns=['FirstName', 'LastName', 'PhoneNumber'],
            data=db_records  # Use database records directly
        )
        
    except Exception as e:
        error_msg = f"Failed to process CSV file: {str(e)}"
        logger.error(f"CSV processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)



@router.get("/get_leads", response_model=List[LeadDB])
async def get_leads(
    receptionist_id: Optional[str] = Query(None, description="Filter by receptionist"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get leads created by the current authenticated user
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - List of leads created by the current user with database IDs and metadata

    Example Response:
    [
    {
        "id": 17,
        "first_name": "Kanoj",
        "last_name": "g",
        "phone_number": "+19132956186",
        "source": "google_sheets",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1xP1MSODD9VRpjQD6Pt-QW_QXdU6qmmrK5cyl_MN0JZM/edit?usp=sharing",
        "filename": null,
        "imported_at": "2025-08-14T19:47:27.821051+00:00",
        "import_source": "google_sheets",
        "created_by_user_id": "5839308a-f881-4809-bbaa-0f9fcdea7107",
        "created_by_user_email": "kanoj2108@gmail.com",
        "vapi_call_id": null,
        "call_status": "pending",
        "call_summary": null,
        "call_recording_url": null,
        "call_transcript": null,
        "success_evaluation": null,
        "created_at": "2025-08-14T19:47:28.428299+00:00",
        "updated_at": "2025-08-14T19:47:28.428299+00:00"
    },
    {
        "id": 16,
        "first_name": "Kanoj",
        "last_name": "g",
        "phone_number": "+19132956186",
        "source": "google_sheets",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1xP1MSODD9VRpjQD6Pt-QW_QXdU6qmmrK5cyl_MN0JZM/edit?usp=sharing",
        "filename": null,
        "imported_at": "2025-08-13T20:29:24.701166+00:00",
        "import_source": "google_sheets",
        "created_by_user_id": "5839308a-f881-4809-bbaa-0f9fcdea7107",
        "created_by_user_email": "kanoj2108@gmail.com",
        "vapi_call_id": "30075607-6adb-4d7f-b2e9-1826e210c349",
        "call_status": "ended",
        "call_summary": "An AI assistant from the CSA San Francisco chapter greeted the caller and offered assistance. The user briefly responded with \"Thank you\" before ending the call. The call concluded without the user stating the reason for their inquiry.",
        "call_recording_url": "https://storage.vapi.ai/30075607-6adb-4d7f-b2e9-1826e210c349-1755117003357-df12ef31-a422-4b39-ba04-abbe3ad7fe6a-mono.wav",
        "call_transcript": "AI: Thank you for calling CSA San Francisco chapter This is Megan, your AI assistant. How may I help you today?\nUser: Thank you.\n",
        "success_evaluation": "false",
        "created_at": "2025-08-13T20:29:25.026151+00:00",
        "updated_at": "2025-08-14T19:48:59.732783+00:00"
    }
    ]
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=400,
                detail="User organization not configured. Please contact administrator."
            )
        
        logger.info(f"Fetching leads for organization: {user_organization.get('name', 'Unknown')}")
        # Base query filtered by organization
        query = supabase.table(table_name).select("*")

        # Map receptionist_id -> assistant_id for filtering outbound calls
        if receptionist_id:
            rec_resp = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).execute()
            assistant_id = rec_resp.data[0]["assistant_id"] if rec_resp.data else None
            if assistant_id:
                query = query.eq("assistant_id", assistant_id)
            else:
                # No assistant for given receptionist, return empty list early
                return []

        result = query.order("created_at", desc=True).execute()
        
        # Check and update leads with missing VAPI call data
        updated_leads = []
        print(f"Result: {result.data}")
        for lead in result.data:
            vapi_call_id = lead.get("vapi_call_id")
            if (vapi_call_id and 
                (lead.get("call_summary") is None or 
                 lead.get("call_recording_url") is None or 
                 lead.get("call_transcript") is None or 
                 lead.get("success_evaluation") is None)):
                
                logger.info(f"Lead {lead.get('id')} has VAPI call ID {vapi_call_id} but missing call data. Fetching from VAPI...")
                
                try:
                    # Fetch call data from VAPI
                    vapi_data = await fetch_vapi_call_data(vapi_call_id)
                    
                    # Update lead with VAPI data
                    updated_lead = await update_lead_with_vapi_data(lead.get('id'), vapi_data, table_name, supabase)
                    
                    if updated_lead:
                        logger.info(f"Successfully updated lead {lead.get('id')} with VAPI call data")
                        updated_leads.append(updated_lead)  # Use updated lead data
                    else:
                        logger.warning(f"Failed to update lead {lead.get('id')} with VAPI call data")
                        updated_leads.append(lead)  # Use original lead data
                        
                except Exception as vapi_error:
                    logger.error(f"Failed to fetch/update VAPI data for lead {lead.get('id')}: {str(vapi_error)}")
                    # Continue with existing lead data if VAPI update fails
                    updated_leads.append(lead)
            else:
                updated_leads.append(lead)
        
        # Log user action
        logger.info(f"User {current_user.get('email', 'unknown')} retrieved {len(updated_leads)} of their own leads from database")
        
        print(f"✅ Retrieved {len(updated_leads)} leads for user {current_user.get('email', 'unknown')} from database")
        
        return updated_leads
        
    except Exception as e:
        logger.error(f"Failed to retrieve leads: {e}")
        print(f"❌ Failed to retrieve leads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve leads: {str(e)}")




@router.post("/get_summary_by_lead_id", response_model=LeadDB)
async def get_summary_by_lead_id(request: LeadIdRequest, current_user: dict = Depends(get_current_user)):
    """
    Get a specific lead by ID (only if created by the current user)
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Parameters:**
    - `lead_id`: The ID of the lead to retrieve (sent in JSON request body)
    
    **Returns:**
    - Lead record if found and owned by current user
    
    **Raises:**
    - 404: If lead not found
    - 403: If lead belongs to another user

    Example Reqest Body:
    {
    "lead_id":14
    }

    Example Response:
    
    {
    "id": 14,
    "first_name": "Kanoj",
    "last_name": "g",
    "phone_number": "+19132956186",
    "source": "google_sheets",
    "sheet_url": "https://docs.google.com/spreadsheets/d/1xP1MSODD9VRpjQD6Pt-QW_QXdU6qmmrK5cyl_MN0JZM/edit?usp=sharing",
    "filename": null,
    "imported_at": "2025-08-13T20:22:41.538362+00:00",
    "import_source": "google_sheets",
    "created_by_user_id": "5839308a-f881-4809-bbaa-0f9fcdea7107",
    "created_by_user_email": "kanoj2108@gmail.com",
    "vapi_call_id": "6e35e88d-9ae1-47f1-b913-9cbad1e2f8ff",
    "call_status": "ended",
    "call_summary": null,
    "call_recording_url": null,
    "call_transcript": null,
    "success_evaluation": "n/a",
    "created_at": "2025-08-13T20:22:41.992643+00:00",
    "updated_at": "2025-08-14T19:49:43.410817+00:00"
    }

    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=400,
                detail="User organization not configured. Please contact administrator."
            )
        
        lead_id = request.lead_id
        print(f"User {current_user.get('email', 'unknown')} requesting lead ID: {lead_id}")
        
        # Get the lead by ID and verify it belongs to user's organization
        result = supabase.table(table_name).select("*").eq("id", lead_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            # Check if lead exists but belongs to another user
            check_lead = supabase.table(table_name).select("id").eq("id", lead_id).execute()
            if check_lead.data:
                logger.warning(f"User {current_user.get('email', 'unknown')} attempted to access lead {lead_id} from another organization")
                raise HTTPException(
                    status_code=403, 
                    detail="Access denied. This lead belongs to another organization."
                )
            else:
                logger.warning(f"User {current_user.get('email', 'unknown')} requested non-existent lead ID: {lead_id}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Lead with ID {lead_id} not found."
                )
        
        lead = result.data[0]
        
        # Check if lead has VAPI call ID but missing call data
        vapi_call_id = lead.get("vapi_call_id")
        if (vapi_call_id and 
            (lead.get("call_summary") is None or 
             lead.get("call_recording_url") is None or 
             lead.get("call_transcript") is None or 
             lead.get("success_evaluation") is None)):
            
            logger.info(f"Lead {lead_id} has VAPI call ID {vapi_call_id} but missing call data. Fetching from VAPI...")
            
            try:
                # Fetch call data from VAPI
                vapi_data = await fetch_vapi_call_data(vapi_call_id)
                
                # Update lead with VAPI data
                updated_lead = await update_lead_with_vapi_data(lead_id, vapi_data, table_name, supabase)
                
                if updated_lead:
                    logger.info(f"Successfully updated lead {lead_id} with VAPI call data")
                    lead = updated_lead  # Use updated lead data
                else:
                    logger.warning(f"Failed to update lead {lead_id} with VAPI call data")
                    
            except Exception as vapi_error:
                logger.error(f"Failed to fetch/update VAPI data for lead {lead_id}: {str(vapi_error)}")
                # Continue with existing lead data if VAPI update fails
                # Don't fail the entire request
        
        # Log user action
        logger.info(f"User {current_user.get('email', 'unknown')} retrieved lead ID: {lead_id}")
        print(f"✅ Retrieved lead ID {lead_id} for user {current_user.get('email', 'unknown')}")
        
        return lead
        
    except HTTPException:
        # Re-raise HTTP exceptions (404, 403)
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve lead {lead_id}: {e}")
        print(f"❌ Failed to retrieve lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lead: {str(e)}")


@router.post("/call_leads", response_model=CallLeadsResponse)
async def call_leads(request: CallLeadsRequest, current_user: dict = Depends(get_current_user)):
    """
    Initiate calls to multiple leads using VAPI
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Parameters:**
    - `lead_ids`: List of lead IDs to call (sent in JSON request body)
    
    **Returns:**
    - Summary of all call attempts with individual results
    
    **Raises:**
    - 400: If no valid leads found
    - 500: If VAPI calls fail

    Example Request Body:
    {
    "lead_ids":[16],
    "voiceId": "Priya"
    }

    Example Response:
    {
    "message": "Call initiation completed with voice 'Priya'. 1 successful, 0 failed out of 1 leads",
    "total_leads": 1,
    "successful_calls": 1,
    "failed_calls": 0,
    "voice_used": "Priya",
    "results": [
        {
            "lead_id": 16,
            "status": "success",
            "customer_name": "Kanoj g",
            "phone_number": "+19132956186",
            "vapi_response": {
                "id": "***",
                "assistantId": "***",
                "phoneNumberId": "***",
                "type": "outboundPhoneCall",
                "createdAt": "2025-08-14T19:54:48.706Z",
                "updatedAt": "2025-08-14T19:54:48.706Z",
                "orgId": "***",
                "cost": 0,
                "customer": {
                    "name": "Kanoj g",
                    "number": "+19132956186"
                },
                "status": "queued",
                "phoneCallProvider": "twilio",
                "phoneCallProviderId": "***",
                "phoneCallTransport": "pstn",
                "monitor": {
                    "listenUrl": "wss://phone-call-websocket.aws-us-west-2-backend-production3.vapi.ai/***/listen",
                    "controlUrl": "https://phone-call-websocket.aws-us-west-2-backend-production3.vapi.ai/***/control"
                },
                "transport": {
                    "callSid": "***",
                    "provider": "twilio",
                    "accountSid": "******"
                }
            }
        }
    ]
}
    """
    try:
        supabase = get_supabase_client()
        table_name = "ai_receptionist_leads"
        
        # Get current user's organization
        user_organization = current_user.get("organization", {})
        organization_id = user_organization.get("id")
        
        if not organization_id:
            logger.error(f"User {current_user.get('email', 'unknown')} has no organization configured")
            raise HTTPException(
                status_code=400,
                detail="User organization not configured. Please contact administrator."
            )
        
        lead_ids = request.lead_ids
        
        if not lead_ids:
            raise HTTPException(
                status_code=400,
                detail="No lead IDs provided"
            )
        
        print(f"User {current_user.get('email', 'unknown')} initiating calls for {len(lead_ids)} leads")
        
        # Get all leads by IDs and verify they belong to user's organization
        result = supabase.table(table_name).select("*").in_("id", lead_ids).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=400,
                detail="No valid leads found for the provided IDs"
            )
        
        # Filter out leads that don't belong to the user
        user_leads = result.data
        requested_ids = set(lead_ids)
        found_ids = {lead["id"] for lead in user_leads}
        missing_ids = requested_ids - found_ids
        
        if missing_ids:
            logger.warning(f"User {current_user.get('email', 'unknown')} attempted to call leads {missing_ids} that don't belong to their organization")
        
        # Initialize results tracking
        results = []
        successful_calls = 0
        failed_calls = 0
        
        # Prepare all customer details for batch VAPI call
        customers_for_vapi = []
        valid_leads = []
        
        for lead in user_leads:
            lead_id = lead["id"]
            phone_number = lead.get("phone_number")
            customer_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
            
            # Validate phone number
            if not phone_number:
                results.append({
                    "lead_id": lead_id,
                    "status": "failed",
                    "error": "Phone number is missing or invalid",
                    "customer_name": customer_name,
                    "phone_number": phone_number
                })
                failed_calls += 1
                continue
            
            # Format phone number with + prefix if not present
            formatted_phone = phone_number
            if not formatted_phone.startswith('+'):
                formatted_phone = f"+{formatted_phone}"
            
            # Add to VAPI customers list
            customers_for_vapi.append({
                "number": formatted_phone,
                "name": customer_name
            })
            valid_leads.append(lead)
        
        # Make single batch VAPI call if we have valid customers
        if customers_for_vapi:
            try:
                # First, update VAPI assistant voice if voiceId is provided
                if hasattr(request, 'voiceId') and request.voiceId:
                    logger.info(f"Updating VAPI assistant voice to '{request.voiceId}' before making calls")
                    try:
                        await update_vapi_assistant_voice(request.voiceId)
                        logger.info(f"Successfully updated VAPI assistant voice to '{request.voiceId}'")
                    except Exception as voice_error:
                        logger.error(f"Failed to update VAPI assistant voice: {str(voice_error)}")
                        # Continue with calls even if voice update fails
                        # But log the error for debugging
                
                # Make batch VAPI call
                vapi_response = await make_vapi_call_batch(customers_for_vapi)
                
                # Update all leads with VAPI call information
                await update_leads_with_call_info_batch(valid_leads, vapi_response, table_name, supabase)
                
                # Process VAPI response results
                vapi_results = vapi_response.get("results", [])
                vapi_errors = vapi_response.get("errors", [])
                
                # Create phone number to VAPI result mapping
                phone_to_result = {}
                for result in vapi_results:
                    customer = result.get("customer", {})
                    phone = customer.get("number")
                    if phone:
                        phone_to_result[phone] = result
                
                # Add successful results
                for lead in valid_leads:
                    lead_id = lead["id"]
                    phone_number = lead.get("phone_number")
                    formatted_phone = f"+{phone_number}" if not phone_number.startswith('+') else phone_number
                    customer_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                    
                    if formatted_phone in phone_to_result:
                        vapi_result = phone_to_result[formatted_phone]
                        results.append({
                            "lead_id": lead_id,
                            "status": "success",
                            "customer_name": customer_name,
                            "phone_number": formatted_phone,
                            "vapi_response": vapi_result
                        })
                        successful_calls += 1
                        logger.info(f"Successfully initiated call for lead ID: {lead_id}")
                    else:
                        results.append({
                            "lead_id": lead_id,
                            "status": "failed",
                            "error": "No VAPI result found for this phone number",
                            "customer_name": customer_name,
                            "phone_number": formatted_phone
                        })
                        failed_calls += 1
                
                logger.info(f"Batch VAPI call successful: {len(vapi_results)} calls initiated")
                
            except Exception as e:
                logger.error(f"Failed to make batch VAPI call: {str(e)}")
                # Mark all valid leads as failed
                for lead in valid_leads:
                    lead_id = lead["id"]
                    customer_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                    phone_number = lead.get("phone_number", "")
                    formatted_phone = f"+{phone_number}" if phone_number and not phone_number.startswith('+') else phone_number
                    
                    results.append({
                        "lead_id": lead_id,
                        "status": "failed",
                        "error": f"VAPI call failed: {str(e)}",
                        "customer_name": customer_name,
                        "phone_number": formatted_phone
                    })
                    failed_calls += 1
        
        # Log overall results
        voice_info = f" with voice '{request.voiceId}'" if hasattr(request, 'voiceId') and request.voiceId else ""
        logger.info(f"User {current_user.get('email', 'unknown')} completed call initiation for {len(lead_ids)} leads{voice_info}: {successful_calls} successful, {failed_calls} failed")
        print(f"✅ Completed call initiation{voice_info}: {successful_calls} successful, {failed_calls} failed out of {len(lead_ids)} leads")
        
        return {
            "message": f"Call initiation completed{voice_info}. {successful_calls} successful, {failed_calls} failed out of {len(lead_ids)} leads",
            "total_leads": len(lead_ids),
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "voice_used": request.voiceId if hasattr(request, 'voiceId') and request.voiceId else None,
            "results": results
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to process call requests: {str(e)}")
        print(f"❌ Failed to process call requests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process call requests: {str(e)}")


async def make_vapi_call_batch(customers: List[dict]) -> dict:
    """
    Make a batch call to VAPI for multiple customers
    
    Args:
        customers: List of customer information (name, number)
        
    Returns:
        VAPI API response with results for all customers
        
    Raises:
        HTTPException: If VAPI call fails
    """
    try:
        # Get VAPI configuration from environment
        vapi_token = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
        vapi_assistant_id = os.getenv("AI_RECEPTION_VAPI_ASSISTANT_ID")
        vapi_phone_number_id = os.getenv("AI_RECEPTION_VAPI_PHONE_NUMBER_ID")
        
        if not all([vapi_token, vapi_assistant_id, vapi_phone_number_id]):
            raise HTTPException(
                status_code=500,
                detail="VAPI configuration is incomplete. Please check environment variables."
            )
        
        # Prepare VAPI request payload
        vapi_payload = {
            "customers": customers,
            "assistantId": vapi_assistant_id,
            "phoneNumberId": vapi_phone_number_id
        }
        
        logger.info(f"Making batch VAPI call for {len(customers)} customers")
        print(vapi_payload)
        # Make request to VAPI
        response = requests.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {vapi_token}"
            },
            json=vapi_payload
        )
        
        response.raise_for_status()
        vapi_data = response.json()
        
        logger.info(f"VAPI batch call successful: {len(vapi_data.get('results', []))} calls initiated")
        return vapi_data
        
    except requests.RequestException as e:
        logger.error(f"VAPI API batch call failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"VAPI API call failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in VAPI batch call: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error in VAPI call: {str(e)}"
        )


async def update_leads_with_call_info_batch(leads_data: List[dict], vapi_response: dict, table_name: str, supabase):
    """
    Update multiple lead records with VAPI call information from batch response
    
    Args:
        leads_data: List of lead data with phone numbers for mapping
        vapi_response: Batch response from VAPI API
        table_name: Database table name
        supabase: Supabase client instance
    """
    try:
        results = vapi_response.get("results", [])
        errors = vapi_response.get("errors", [])
        
        logger.info(f"Processing VAPI batch response: {len(results)} successful calls, {len(errors)} errors")
        
        # Create a mapping of phone number to VAPI result
        phone_to_result = {}
        for result in results:
            customer = result.get("customer", {})
            phone = customer.get("number")
            if phone:
                phone_to_result[phone] = result
        
        # Update each lead with corresponding VAPI call information
        for lead in leads_data:
            lead_id = lead["id"]
            phone_number = lead.get("phone_number")
            
            if phone_number and phone_number in phone_to_result:
                vapi_result = phone_to_result[phone_number]
                
                # Extract relevant information from VAPI result
                call_id = vapi_result.get("id")
                call_status = vapi_result.get("status", "pending")
                
                # Update lead with call information
                update_data = {
                    "vapi_call_id": call_id,
                    "call_status": call_status,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Update the lead record
                result = supabase.table(table_name).update(update_data).eq("id", lead_id).execute()
                
                if result.data:
                    logger.info(f"Successfully updated lead {lead_id} with VAPI call ID: {call_id}")
                else:
                    logger.warning(f"No data returned when updating lead {lead_id} with VAPI call information")
            else:
                logger.warning(f"No VAPI result found for lead {lead_id} with phone {phone_number}")
                
    except Exception as e:
        logger.error(f"Failed to update leads with VAPI call information: {str(e)}")
        # Don't raise exception here as the main call was successful
        # Just log the error for debugging


async def fetch_vapi_call_data(vapi_call_id: str) -> dict:
    """
    Fetch call data from VAPI API for a specific call ID
    
    Args:
        vapi_call_id: The VAPI call ID to fetch data for
        
    Returns:
        VAPI call data dictionary
        
    Raises:
        HTTPException: If VAPI API call fails
    """
    try:
        # Get VAPI configuration from environment
        vapi_token = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
        
        if not vapi_token:
            logger.error("VAPI auth token not configured")
            raise HTTPException(status_code=500, detail="VAPI configuration missing")
        
        # Make request to VAPI to get call details
        headers = {
            "Authorization": f"Bearer {vapi_token}"
        }
        
        url = f"https://api.vapi.ai/call/{vapi_call_id}"
        logger.info(f"Fetching VAPI call data for call ID: {vapi_call_id}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        vapi_data = response.json()
        logger.info(f"Successfully fetched VAPI call data for call ID: {vapi_call_id}")
        
        return vapi_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"VAPI API request failed for call {vapi_call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch VAPI call data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching VAPI call data for {vapi_call_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch VAPI call data: {str(e)}")


# @router.get("/get_vapi_voice_id/{display_name}", response_model=VapiVoiceIdResponse)
# async def get_vapi_voice_id(display_name: str, current_user: dict = Depends(get_current_user)):
#     """
#     Get VAPI voice ID for a given display name
    
#     **Authentication Required**: Include `Authorization: Bearer <token>` header
    
#     **Parameters:**
#     - `display_name`: The display name of the voice agent (e.g., "Alex", "Maya")
    
#     **Returns:**
#     - VAPI voice ID for the given display name
    
#     **Raises:**
#     - 404: If display name not found
#     """
#     try:
        
#         # Display name mapping: Frontend names to backend names
#         display_to_backend_mapping = {
#             "Alex": "cole",
#             "Maya": "harry",
#             "Jordan": "spencer",
#             "Priya": "neha",
#             "Emma": "kylie",
#             "Grace": "savannah",
#             "Sophie": "paige",
#             "Arjun": "rohan",
#             "Luna": "hana",
#             "Max": "elliot"
#         }
        
#         if display_name not in display_to_backend_mapping:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Voice agent '{display_name}' not found. Available names: {list(display_to_backend_mapping.keys())}"
#             )
        
#         # Get backend name from display name
#         backend_name = display_to_backend_mapping[display_name]
#         # Get VAPI voice ID from backend name
#         vapi_voice_id = backend_voice_mapping[backend_name]
#         logger.info(f"User {current_user.get('email', 'unknown')} requested VAPI voice ID for '{display_name}': {vapi_voice_id}")
        
#         return {
#             "display_name": display_name,
#             "vapi_voice_id": vapi_voice_id,
#             "message": f"Successfully retrieved VAPI voice ID for {display_name}"
#         }
        
#     except HTTPException:
#         # Re-raise HTTP exceptions
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error getting VAPI voice ID for '{display_name}': {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get VAPI voice ID: {str(e)}")


# @router.get("/get_backend_voice_name/{display_name}", response_model=VapiBackendVoiceResponse)
# async def get_backend_voice_name(display_name: str, current_user: dict = Depends(get_current_user)):
#     """
#     Get backend voice name for a given display name (for VAPI assistant updates)
    
#     **Authentication Required**: Include `Authorization: Bearer <token>` header
    
#     **Parameters:**
#     - `display_name`: The display name of the voice agent (e.g., "Alex", "Maya")
    
#     **Returns:**
#     - Backend voice name (e.g., "cole", "harry") for VAPI assistant updates
    
#     **Raises:**
#     - 404: If display name not found
#     """
#     try:
#         # Display name mapping: Frontend names to backend names
#         display_to_backend_mapping = {
#             "Alex": "cole",
#             "Maya": "harry",
#             "Jordan": "spencer",
#             "Priya": "neha",
#             "Emma": "kylie",
#             "Grace": "savannah",
#             "Sophie": "paige",
#             "Arjun": "rohan",
#             "Luna": "hana",
#             "Max": "elliot"
#         }
        
#         if display_name not in display_to_backend_mapping:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Voice agent '{display_name}' not found. Available names: {list(display_to_backend_mapping.keys())}"
#             )
        
#         # Get backend name from display name
#         backend_name = display_to_backend_mapping[display_name]
#         logger.info(f"User {current_user.get('email', 'unknown')} requested backend voice name for '{display_name}': {backend_name}")
        
#         return {
#             "display_name": display_name,
#             "backend_name": backend_name,
#             "message": f"Successfully retrieved backend voice name for {display_name}"
#         }
        
#     except HTTPException:
#         # Re-raise HTTP exceptions
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error getting backend voice name for '{display_name}': {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to get backend voice name: {str(e)}")


async def update_vapi_assistant_voice(voiceId: str) -> bool:
    """
    Update VAPI assistant with new voice
    
    Args:
        voiceId: Voice agent name from UI (e.g., "Maya", "Alex")
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        HTTPException: If VAPI API call fails
    """
    try:
        # Get VAPI configuration from environment
        vapi_token = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
        vapi_assistant_id = os.getenv("AI_RECEPTION_VAPI_ASSISTANT_ID")
        
        if not all([vapi_token, vapi_assistant_id]):
            logger.error("VAPI configuration missing for assistant voice update")
            raise HTTPException(status_code=500, detail="VAPI configuration incomplete")
        
        # Display name mapping: Frontend names to backend names
        display_to_backend_mapping = {
            "Alex": "cole",
            "Maya": "harry",
            "Jordan": "spencer",
            "Priya": "neha",
            "Emma": "kylie",
            "Grace": "savannah",
            "Sophie": "paige",
            "Arjun": "rohan",
            "Luna": "hana",
            "Max": "elliot"
        }
        
        if voiceId not in display_to_backend_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice ID '{voiceId}'. Available voices: {list(display_to_backend_mapping.keys())}"
            )
        
        # Get backend name from display name
        backend_voice_name = display_to_backend_mapping[voiceId]
        
        # Make request to VAPI to update assistant voice
        headers = {
            "Authorization": f"Bearer {vapi_token}"
        }
        
        url = f"https://api.vapi.ai/assistant/{vapi_assistant_id}"
        payload = {
            "voice": {
                "provider": "vapi",
                "voiceId": backend_voice_name
            }
        }
        
        logger.info(f"Updating VAPI assistant {vapi_assistant_id} voice to '{backend_voice_name}' (UI: '{voiceId}')")
        
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        
        logger.info(f"Successfully updated VAPI assistant voice to '{backend_voice_name}'")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"VAPI API request failed for assistant voice update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update VAPI assistant voice: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error updating VAPI assistant voice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update VAPI assistant voice: {str(e)}")


async def update_lead_with_vapi_data(lead_id: str, vapi_data: dict, table_name: str, supabase):
    """
    Update a lead with VAPI call data
    
    Args:
        lead_id: The lead ID to update
        vapi_data: VAPI call data dictionary
        table_name: Database table name
        supabase: Supabase client
        
    Returns:
        Updated lead data
    """
    try:
        # Extract relevant data from VAPI response
        success_evaluation = vapi_data.get("analysis", {}).get("successEvaluation")
        if not success_evaluation:
            success_evaluation = "n/a"
        
        update_data = {
            "call_status": vapi_data.get("status"),
            "call_summary": vapi_data.get("analysis", {}).get("summary"),
            "call_recording_url": vapi_data.get("recordingUrl"),
            "call_transcript": vapi_data.get("transcript"),
            "success_evaluation": success_evaluation,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update database
        result = supabase.table(table_name).update(update_data).eq("id", lead_id).execute()
        
        if result.data:
            logger.info(f"Successfully updated lead {lead_id} with VAPI call data")
            return result.data[0]
        else:
            logger.warning(f"No data returned when updating lead {lead_id} with VAPI call data")
            return None
            
    except Exception as e:
        logger.error(f"Failed to update lead {lead_id} with VAPI call data: {str(e)}")
        raise


@router.post("/vapi/webhook")
async def vapi_webhook(
    request: dict,
    x_webhook_secret: str = Header(..., alias="X-Webhook-Secret")
):
    """
    VAPI webhook endpoint to handle call events
    
    **Security**: Include `X-Webhook-Secret` header with your webhook secret key
    
    **Webhook Events:**
    - call-started: Call begins
    - speech-update: User speech detected
    - function-call: Function execution requested
    - call-ended: Call completes
    
    **Returns:**
    - 200: Webhook processed successfully
    - 401: Invalid webhook secret
    - 400: Invalid webhook data
    - 500: Processing error
    """
    try:
        # Validate webhook secret
        expected_secret = VAPI_WEBHOOK_SECRET
        if not expected_secret:
            logger.error("AI_RECEPTION_VAPI_WEBHOOK_SECRET environment variable not set")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        if x_webhook_secret != expected_secret:
            logger.warning(f"Invalid webhook secret received: {x_webhook_secret[:10]}...")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Extract webhook data
        message_data = request.get("message", {})
        webhook_type = message_data.get("type")
        timestamp = message_data.get("timestamp")
        call_data = message_data.get("call", {})
        
        logger.info(f"VAPI webhook received: {webhook_type} at {timestamp}")
        
        # Only process end-of-call-report webhooks
        if webhook_type == "end-of-call-report":
            # Extract call details from the message structure
            
            # Get call ID from the call object
            call_id = call_data.get("id")
            call_type = call_data.get("type")
            
            # Get recording URL (from message level)
            recording_url = message_data.get("recordingUrl", "No recording URL")
            
            # Get summary (from message.analysis)
            summary = message_data.get("analysis", {}).get("summary", "No summary available")
            
            # Get transcript (from message level)
            transcript = message_data.get("transcript", "No transcript available")
            
            # Get success evaluation (from message.analysis)
            success_eval = message_data.get("analysis", {}).get("successEvaluation", "No evaluation")
            
            # Get call duration (from message level)
            duration_seconds = message_data.get("durationSeconds", "Unknown")
            
            # Get additional useful information
            ended_reason = message_data.get("endedReason", "Unknown")
            cost = message_data.get("cost", "Unknown")
            customer_number = call_data.get("customer", {}).get("number", "Unknown")
            phone_number = request.get("phoneNumber", {}).get("number", "Unknown")
            
            # Print to console
            print("🎯 VAPI END-OF-CALL REPORT RECEIVED")
            print("=" * 60)
            print(f"📞 Call ID: {call_id}")
            print(f"📱 Customer Number: {customer_number}")
            print(f"📞 Phone Number: {phone_number}")
            print(f"🎵 Recording URL: {recording_url}")
            print(f"📝 Summary: {summary}")
            print(f"📊 Success Evaluation: {success_eval}")
            print(f"⏱️  Duration: {duration_seconds} seconds")
            print(f"💸 Cost: ${cost}")
            print(f"🔚 Ended Reason: {ended_reason}")
            print(f"📄 Transcript: {transcript[:200]}..." if len(transcript) > 200 else f"📄 Transcript: {transcript}")
            print("=" * 60)
            
            # Log to logger as well
            logger.info(f"End-of-call report received for call {call_id}")
            logger.info(f"Customer Number: {customer_number}")
            logger.info(f"Phone Number: {phone_number}")
            logger.info(f"Recording URL: {recording_url}")
            logger.info(f"Summary: {summary}")
            logger.info(f"Success Evaluation: {success_eval}")
            logger.info(f"Duration: {duration_seconds} seconds")
            logger.info(f"Cost: ${cost}")
            logger.info(f"Ended Reason: {ended_reason}")
            
            # Prepare call data for database
            call_data_for_db = {
                "vapi_call_id": call_id,
                "call_status": "ended",
                "call_summary": summary,
                "call_recording_url": recording_url,
                "call_transcript": transcript,
                "success_evaluation": success_eval,
                "call_type": call_type,
                "call_duration_seconds": duration_seconds,
                "call_cost": cost,
                "ended_reason": ended_reason,
                "customer_number": customer_number,
                "phone_number_id": phone_number
            }
            
            # Import database operations
            from app.database_operations import save_inbound_call_data, update_outbound_call_data, get_organization_by_vapi_org_id
            
            try:
                # Get organization ID from VAPI org ID in the webhook payload
                vapi_org_id = call_data.get("orgId")
                if not vapi_org_id:
                    logger.error("No VAPI org ID found in webhook payload")
                    raise HTTPException(status_code=400, detail="VAPI org ID is required in webhook payload")
                
                organization = await get_organization_by_vapi_org_id(vapi_org_id)
                if not organization:
                    logger.error(f"Organization not found for VAPI org ID: {vapi_org_id}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Organization not configured for VAPI org ID: {vapi_org_id}. Please configure this organization in the database."
                    )
                
                organization_id = organization["id"]
                logger.info(f"Found organization: {organization['name']} for VAPI org ID: {vapi_org_id}")
                
                # Save call data based on call type
                if call_type == "inboundPhoneCall":
                    # Save to inbound calls table
                    saved_call = await save_inbound_call_data(call_data_for_db, organization_id)
                    if saved_call:
                        logger.info(f"Successfully saved inbound call data for call ID: {call_id}")
                        print(f"💾 Saved inbound call data to database")
                    else:
                        logger.warning(f"Failed to save inbound call data for call ID: {call_id}")
                        
                elif call_type == "outboundPhoneCall":
                    # Update existing lead in leads table
                    updated_lead = await update_outbound_call_data(call_data_for_db, organization_id)
                    if updated_lead:
                        logger.info(f"Successfully updated outbound call data for call ID: {call_id}")
                        print(f"💾 Updated outbound call data in leads table")
                    else:
                        logger.warning(f"Failed to update outbound call data for call ID: {call_id}")
                        
                else:
                    logger.warning(f"Unknown call type: {call_type}")
                    print(f"⚠️  Unknown call type: {call_type}")
                    
            except Exception as e:
                logger.error(f"Error saving call data to database: {str(e)}")
                print(f"❌ Error saving call data: {str(e)}")
                # Don't raise exception - webhook should still succeed
            
        else:
            logger.warning(f"Unsupported webhook type: {webhook_type}. Only 'end-of-call-report' is supported.")
            return {"status": "unsupported_type", "message": f"Only 'end-of-call-report' webhooks are supported. Received: {webhook_type}"}
        
        return {"status": "success", "message": f"Webhook {webhook_type} processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing VAPI webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


class CallNumberRequest(BaseModel):
    receptionist_id: str
    phone: str
    first_name: str | None = None
    last_name: str | None = None

class CallNumberResponse(BaseModel):
    message: str
    vapi_call_id: str

@router.post("/call_number", response_model=CallNumberResponse)
async def call_number(
    payload: CallNumberRequest,
    current_user: dict = Depends(get_current_user)
):
    """Trigger a single outbound call via Vapi and store/ update the lead record."""
    supabase = get_supabase_client()

    # Get receptionist row to obtain assistant_id
    rec_resp = supabase.table("receptionists").select("assistant_id,name").eq("id", payload.receptionist_id).execute()
    if not rec_resp.data:
        raise HTTPException(status_code=404, detail="Receptionist not found")
    assistant_id = rec_resp.data[0].get("assistant_id")
    if not assistant_id:
        raise HTTPException(status_code=400, detail="Receptionist has no assistant configured")

    # fetch phone_number row for this assistant to get vapi_id
    phone_row = supabase.table("phone_numbers").select("vapi_id").eq("assistant_id", assistant_id).single().execute()
    phone_number_id = phone_row.data.get("vapi_id") if phone_row.data else None

    if not phone_number_id:
        raise HTTPException(status_code=400, detail="Assistant not linked to any phone number")

    phone_e164 = payload.phone if payload.phone.startswith("+") else f"+1{payload.phone}"
    full_name = (payload.first_name or "") + (f" {payload.last_name}" if payload.last_name else "")

    print("phone_number_id", phone_number_id)
    print("assistant_id", assistant_id)
    print("phone_e164", phone_e164)
    print("full_name", full_name)

    vapi_payload = {
        "assistantId": assistant_id,
        "customer": {
            "number": phone_e164,
            "numberE164CheckEnabled": False
        },
        "phoneNumberId": phone_number_id
    }
    vapi_token = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
    if not vapi_token:
        raise HTTPException(status_code=500, detail="Vapi auth token missing")

    async with httpx.AsyncClient(timeout=30) as client:
        vapi_res = await client.post(
            "https://api.vapi.ai/call/phone",
            headers={"Authorization": f"Bearer {vapi_token}", "Content-Type": "application/json"},
            json=vapi_payload,
        )
        if not 200 <= vapi_res.status_code < 300:
            raise HTTPException(status_code=500, detail=f"Vapi error: {vapi_res.text}")
        vapi_data = vapi_res.json()
        call_id = vapi_data.get("id")

    # Upsert lead
    lead_table = "ai_receptionist_leads"
    lead_data = {
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "phone_number": payload.phone,
        "assistant_id": assistant_id,
        "source": "quick_call",
        "import_source": "quick_call",
        "vapi_call_id": call_id,
        "call_status": "initiated",
    }
    supabase.table(lead_table).insert(lead_data).execute()

    return CallNumberResponse(message="Call initiated", vapi_call_id=call_id)


