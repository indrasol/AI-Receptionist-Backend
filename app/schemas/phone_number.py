from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PhoneNumberBase(BaseModel):
    """Base schema for phone number data"""
    phone_id: str = Field(..., description="External identifier (e.g., phone_001)")
    number: str = Field(..., description="The actual phone number in international format")
    provider: str = Field(..., description="Service provider (Twilio, Vonage, etc.)")
    country: str = Field(..., description="Country code (US, UK, CA, etc.)")
    country_code: str = Field(..., description="International dialing code (+1, +44, etc.)")
    type: str = Field(default="local", description="Type: local, toll-free, mobile, international")
    area_code: Optional[str] = Field(None, description="Area code of the phone number")
    status: str = Field(default="active", description="Status: active, inactive, suspended, pending")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_default: bool = Field(default=False, description="Whether this is the default phone number")
    monthly_cost: Decimal = Field(default=0.00, description="Monthly cost for this phone number")

class PhoneNumberCreate(PhoneNumberBase):
    """Schema for creating a new phone number"""
    organization_id: str = Field(..., description="Organization ID that owns this phone number")

class PhoneNumberUpdate(BaseModel):
    """Schema for updating phone number data"""
    number: Optional[str] = None
    provider: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    type: Optional[str] = None
    area_code: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    monthly_cost: Optional[Decimal] = None

class PhoneNumberDB(PhoneNumberBase):
    """Schema for phone number data from database"""
    id: str = Field(..., description="Unique identifier")
    organization_id: str = Field(..., description="Organization ID")
    usage_count: int = Field(default=0, description="Number of times used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by_user_id: Optional[str] = Field(None, description="User who created this record")

    class Config:
        from_attributes = True

class PhoneNumberResponse(PhoneNumberDB):
    """Schema for phone number API responses"""
    pass

class PhoneNumberListResponse(BaseModel):
    """Schema for phone number list responses"""
    message: str
    phone_numbers: List[PhoneNumberResponse]
    total_count: int

class PhoneNumberSearchRequest(BaseModel):
    """Schema for phone number search requests"""
    country: Optional[str] = None
    provider: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class PhoneNumberSearchResponse(BaseModel):
    """Schema for phone number search responses"""
    message: str
    phone_numbers: List[PhoneNumberResponse]
    total_count: int
    filtered_count: int
    
class PhoneNumberUsageUpdate(BaseModel):
    """Schema for updating phone number usage statistics"""
    phone_id: str = Field(..., description="Phone ID to update usage for")
    increment_usage: bool = Field(default=True, description="Whether to increment usage count")

class PhoneNumberStats(BaseModel):
    """Schema for phone number statistics"""
    total_numbers: int
    active_numbers: int
    inactive_numbers: int
    by_country: dict
    by_provider: dict
    by_type: dict
    total_monthly_cost: Decimal
    most_used_number: Optional[PhoneNumberResponse] = None

class PhoneNumberStatsResponse(BaseModel):
    """Schema for phone number statistics response"""
    message: str
    stats: PhoneNumberStats
