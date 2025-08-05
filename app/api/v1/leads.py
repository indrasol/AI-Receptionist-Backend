from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.lead import Lead, LeadResponse, LeadList, LeadDB
import logging
import pandas as pd
import io
from app.database import get_supabase_client
from app.config import settings
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-excel", response_model=LeadResponse)
async def upload_leads_excel(file: UploadFile = File(...)):
    """
    Upload Excel file and parse leads into database
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
    
    print("=" * 50)
    print("EXCEL LEAD UPLOAD")
    print("=" * 50)
    print(f"File: {file.filename}")
    print(f"Size: {file.size} bytes")
    print("=" * 50)
    
    leads_processed = 0
    leads_saved = 0
    errors = []
    
    try:
        # Read Excel file
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        print(f"Excel file loaded with {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Validate required columns for simple Excel format
        required_columns = ['first_name', 'last_name', 'phone_number']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}. Your Excel should have: first_name, last_name, phone_number"
            )
        
        # Connect to Supabase
        supabase = get_supabase_client()
        
        # Use your existing table name from configuration
        table_name = settings.leads_table_name
        
        # Debug: Print connection info
        print(f"🔍 Database Debug Info:")
        print(f"   Table name: {table_name}")
        print(f"   Supabase URL: {settings.supabase_url}")
        print(f"   Debug mode: {settings.debug}")
        
        # Process each row
        for index, row in df.iterrows():
            leads_processed += 1
            
            try:
                # Create lead data for simple Excel format
                lead_data = {
                    "first_name": str(row['first_name']).strip(),
                    "last_name": str(row['last_name']).strip(),
                    "phone_number": str(row['phone_number']).strip(),
                    "call_pass": row.get('call_pass', None) if pd.notna(row.get('call_pass')) else None,
                    "booking_success": row.get('booking_success', None) if pd.notna(row.get('booking_success')) else None
                }
                
                # Validate phone format (basic check)
                if not lead_data['phone_number'] or len(lead_data['phone_number']) < 7:
                    errors.append(f"Row {index + 1}: Invalid phone format - {lead_data['phone_number']}")
                    continue
                
                # Check if lead already exists (by phone number)
                existing = supabase.table(table_name).select("id").eq("phone_number", lead_data['phone_number']).execute()
                
                if existing.data:
                    # Update existing lead
                    supabase.table(table_name).update(lead_data).eq("phone_number", lead_data['phone_number']).execute()
                    print(f"✅ Updated existing lead: {lead_data['first_name']} {lead_data['last_name']} ({lead_data['phone_number']})")
                else:
                    # Insert new lead
                    result = supabase.table(table_name).insert(lead_data).execute()
                    print(f"✅ Saved new lead: {lead_data['first_name']} {lead_data['last_name']} ({lead_data['phone_number']})")
                
                leads_saved += 1
                
            except Exception as e:
                error_msg = f"Row {index + 1}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                print(f"❌ Error processing row {index + 1}: {e}")
        
        # Log summary
        logger.info(f"Excel upload completed: {leads_saved}/{leads_processed} leads saved")
        print(f"✅ Excel upload completed: {leads_saved}/{leads_processed} leads saved")
        
        if errors:
            print(f"⚠️  {len(errors)} errors encountered")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        return LeadResponse(
            detail=f"Excel file processed successfully",
            leads_processed=leads_processed,
            leads_saved=leads_saved,
            errors=errors if errors else None
        )
        
    except Exception as e:
        logger.error(f"Failed to process Excel file: {e}")
        print(f"❌ Failed to process Excel file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process Excel file: {str(e)}")


@router.post("/bulk", response_model=LeadResponse)
async def create_leads_bulk(leads: LeadList):
    """
    Create multiple leads from JSON data
    """
    print("=" * 50)
    print("BULK LEAD CREATION")
    print("=" * 50)
    print(f"Leads to process: {len(leads.leads)}")
    print("=" * 50)
    
    leads_processed = 0
    leads_saved = 0
    errors = []
    
    try:
        supabase = get_supabase_client()
        table_name = settings.leads_table_name
        
        for lead in leads.leads:
            leads_processed += 1
            
            try:
                lead_data = {
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "phone_number": lead.phone_number,
                    "call_pass": lead.call_pass,
                    "booking_success": lead.booking_success
                }
                
                # Check if lead already exists (by phone)
                existing = supabase.table(table_name).select("id").eq("phone_number", lead.phone_number).execute()
                
                if existing.data:
                    # Update existing
                    supabase.table(table_name).update(lead_data).eq("phone_number", lead.phone_number).execute()
                    print(f"✅ Updated existing lead: {lead.first_name} {lead.last_name} ({lead.phone_number})")
                else:
                    # Insert new
                    result = supabase.table(table_name).insert(lead_data).execute()
                    print(f"✅ Saved new lead: {lead.first_name} {lead.last_name} ({lead.phone_number})")
                
                leads_saved += 1
                
            except Exception as e:
                error_msg = f"Lead {leads_processed}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                print(f"❌ Error processing lead {leads_processed}: {e}")
        
        logger.info(f"Bulk lead creation completed: {leads_saved}/{leads_processed} leads saved")
        print(f"✅ Bulk lead creation completed: {leads_saved}/{leads_processed} leads saved")
        
        return LeadResponse(
            detail=f"Bulk lead creation completed",
            leads_processed=leads_processed,
            leads_saved=leads_saved,
            errors=errors if errors else None
        )
        
    except Exception as e:
        logger.error(f"Failed to create leads: {e}")
        print(f"❌ Failed to create leads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create leads: {str(e)}")


@router.get("/", response_model=List[LeadDB])
async def get_leads():
    """
    Get all leads from database
    """
    try:
        supabase = get_supabase_client()
        table_name = settings.leads_table_name
        
        result = supabase.table(table_name).select("*").order("created_at", desc=True).execute()
        
        print(f"✅ Retrieved {len(result.data)} leads from database")
        
        return result.data
        
    except Exception as e:
        logger.error(f"Failed to retrieve leads: {e}")
        print(f"❌ Failed to retrieve leads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve leads: {str(e)}") 