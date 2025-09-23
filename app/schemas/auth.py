from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserSignupRequest(BaseModel):
    """Request model for user signup"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")
    username: str = Field(..., min_length=3, max_length=50, description="User's username (3-50 characters)")
    first_name: Optional[str] = Field(None, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User's last name")

class UserSigninRequest(BaseModel):
    """Request model for user signin"""
    identifier: str = Field(..., description="User's email or username")
    password: str = Field(..., description="User's password")

class UserResponse(BaseModel):
    """Response model for user data"""
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: str
    updated_at: str

class AuthResponse(BaseModel):
    """Response model for authentication"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class SignupResponse(BaseModel):
    """Response model for signup"""
    message: str
    user: UserResponse

class SigninResponse(BaseModel):
    """Response model for signin"""
    message: str
    auth: AuthResponse

class LogoutResponse(BaseModel):
    """Response model for logout"""
    message: str

class TokenVerifyRequest(BaseModel):
    """Request model for token verification"""
    token: str

class TokenVerifyResponse(BaseModel):
    """Response model for token verification"""
    valid: bool
    claims: Optional[dict] = None
    message: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """Request model for password reset"""
    email: EmailStr

class PasswordResetResponse(BaseModel):
    """Response model for password reset"""
    message: str


# --------------------------- OTP signup flow ---------------------------


class OtpRequest(BaseModel):
    """Payload for requesting an email OTP during signup"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None


class OtpVerifyRequest(BaseModel):
    """Payload for verifying an OTP code sent to email"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit numeric code")


class GenericMessage(BaseModel):
    """Simple message-only response"""
    message: str 