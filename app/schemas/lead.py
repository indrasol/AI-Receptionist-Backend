from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class Lead(BaseModel):
    """Individual lead schema for simple Excel format"""
    id: Optional[str] = None
    first_name: str
    last_name: str
    phone_number: str  # Changed from 'phone' to 'phone_number'
    created_at: Optional[str] = None
    call_pass: Optional[bool] = None
    booking_success: Optional[bool] = None


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
    """Schema for lead response from database - completely flexible"""
    model_config = ConfigDict(extra='allow')  # Allow any extra fields from database 