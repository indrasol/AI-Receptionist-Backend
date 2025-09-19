from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Union
from datetime import datetime


class Lead(BaseModel):
    """Individual lead schema for simple Excel format"""
    id: Optional[str] = None
    first_name: str
    last_name: str
    phone_number: str
    created_at: Optional[Union[str, datetime]] = None


class LeadResponse(BaseModel):
    """Response schema for lead operations"""
    detail: str
    leads_processed: int
    leads_saved: int
    errors: Optional[List[str]] = None


class LeadList(BaseModel):
    """Schema for list of leads"""
    leads: List[Lead]


class LeadDB(BaseModel):
    """Schema for lead response from database - matches ai_receptionist_leads table structure"""
    
    # Core lead information
    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    
    # Source and import information
    source: Optional[str] = None
    sheet_url: Optional[str] = None
    filename: Optional[str] = None
    imported_at: Optional[Union[str, datetime]] = None
    import_source: Optional[str] = None
    
    # User tracking
    created_by_user_id: Optional[str] = None
    created_by_user_email: Optional[str] = None
    
    # VAPI call information
    vapi_call_id: Optional[str] = None
    call_status: Optional[str] = None
    
    # Call details from VAPI
    call_summary: Optional[str] = None
    call_recording_url: Optional[str] = None
    call_transcript: Optional[str] = None
    success_evaluation: Optional[str] = None
    
    # Timestamps
    created_at: Optional[Union[str, datetime]] = None
    updated_at: Optional[Union[str, datetime]] = None


class GoogleSheetsResponse(BaseModel):
    """Response schema for Google Sheets operations"""
    message: str
    rows_count: int
    columns: List[str]
    data: List[dict]  # The actual sheet data with embedded database IDs


class LeadIdRequest(BaseModel):
    """Request schema for getting a lead by ID"""
    lead_id: str


class CallLeadsRequest(BaseModel):
    """Request schema for calling multiple leads"""
    lead_ids: List[str]
    voiceId: str  # Voice agent name from UI (e.g., "Maya", "Alex")


class CallLeadResponse(BaseModel):
    """Response schema for call_lead endpoint"""
    message: str
    lead_id: str
    customer_name: str
    phone_number: str
    vapi_response: dict


class CallLeadsResponse(BaseModel):
    """Response schema for call_leads endpoint"""
    message: str
    total_leads: int
    successful_calls: int
    failed_calls: int
    voice_used: Optional[str] = None  # Voice agent name used for the calls
    results: List[dict]  # List of call results for each lead


class VapiVoicesResponse(BaseModel):
    """Response schema for VAPI voice agents list"""
    message: str
    assistants: List[dict]  # List of VAPI voice agents
    total_count: int


class VapiPhoneNumbersResponse(BaseModel):
    """Response schema for VAPI available phone numbers list"""
    message: str
    phone_numbers: List[dict]  # List of available phone numbers
    total_count: int


class VapiVoiceIdResponse(BaseModel):
    """Response schema for VAPI voice ID lookup"""
    display_name: str
    vapi_voice_id: str
    message: str


class VapiBackendVoiceResponse(BaseModel):
    """Response schema for backend voice name lookup"""
    display_name: str
    backend_name: str
    message: str 