from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Union
from datetime import datetime


class Lead(BaseModel):
    """Individual lead schema for simple Excel format"""
    id: Optional[int] = None
    first_name: str
    last_name: str
    phone_number: str  # Changed from 'phone' to 'phone_number'
    created_at: Optional[Union[str, datetime]] = None
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
    """Schema for lead response from database - flexible to handle any columns"""
    model_config = ConfigDict(extra='allow')  # Allow extra fields
    
    id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: Optional[Union[str, datetime]] = None
    call_pass: Optional[bool] = None
    booking_success: Optional[bool] = None 