from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.auth import (
    UserSignupRequest, UserSigninRequest, TokenVerifyRequest,
    SignupResponse, SigninResponse, LogoutResponse, 
    TokenVerifyResponse, PasswordResetRequest, PasswordResetResponse
)
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Initialize auth service
auth_service = AuthService()

@router.post("/signup", response_model=SignupResponse, tags=["authentication"])
async def signup_user(user_data: UserSignupRequest):
    """
    Register a new user account
    
    - **email**: User's email address (must be unique)
    - **password**: User's password (minimum 8 characters)
    - **username**: User's username (3-50 characters, must be unique)
    - **first_name**: User's first name (optional)
    - **last_name**: User's last name (optional)
    """
    try:
        user = await auth_service.signup_user(user_data)
        
        return SignupResponse(
            message="User registered successfully",
            user=user
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during signup")

@router.post("/signin", response_model=SigninResponse, tags=["authentication"])
async def signin_user(credentials: UserSigninRequest):
    """
    Authenticate user and return access tokens
    
    - **identifier**: User's email or username
    - **password**: User's password
    """
    try:
        auth_data = await auth_service.signin_user(credentials)
        
        return SigninResponse(
            message="User authenticated successfully",
            auth=auth_data
        )
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Signin error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during signin")

@router.post("/logout", response_model=LogoutResponse, tags=["authentication"])
async def logout_user(refresh_token: str = Header(..., alias="refresh-token")):
    """
    Logout user by invalidating refresh token
    
    - **refresh-token**: User's refresh token (sent in header)
    """
    try:
        success = await auth_service.logout_user(refresh_token)
        
        if success:
            return LogoutResponse(message="User logged out successfully")
        else:
            raise HTTPException(status_code=400, detail="Failed to logout user")
            
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during logout")

@router.post("/token/verify", response_model=TokenVerifyResponse, tags=["authentication"])
async def verify_token(payload: TokenVerifyRequest):
    """
    Verify JWT token and return validation status
    
    - **token**: JWT token to verify
    """
    try:
        result = await auth_service.verify_token(payload.token)
        
        if result["valid"]:
            return TokenVerifyResponse(
                valid=True,
                claims=result["claims"]
            )
        else:
            return TokenVerifyResponse(
                valid=False,
                message=result["message"]
            )
            
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during token verification")

@router.post("/password/reset", response_model=PasswordResetResponse, tags=["authentication"])
async def reset_password(payload: PasswordResetRequest):
    """
    Send password reset email to user
    
    - **email**: User's email address
    """
    try:
        success = await auth_service.reset_password(payload.email)
        
        if success:
            return PasswordResetResponse(
                message="Password reset email sent successfully. Check your email for further instructions."
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to send password reset email")
            
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during password reset")

@router.get("/me", tags=["authentication"])
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current user information from JWT token
    
    Requires valid Bearer token in Authorization header
    """
    try:
        # Extract token from Bearer header
        token = credentials.credentials
        
        # Verify token
        result = await auth_service.verify_token(token)
        
        if not result["valid"]:
            raise HTTPException(status_code=401, detail=result["message"])
        
        # Return user claims from token
        claims = result["claims"]
        return {
            "user_id": claims.get("sub"),
            "email": claims.get("email"),
            "username": claims.get("user_metadata", {}).get("username"),
            "first_name": claims.get("user_metadata", {}).get("first_name"),
            "last_name": claims.get("user_metadata", {}).get("last_name"),
            "exp": claims.get("exp"),
            "iat": claims.get("iat")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------
# OTP signup endpoints
# ---------------------------------------------------------------------


from app.schemas.auth import OtpRequest, OtpVerifyRequest, GenericMessage  # noqa: E402


@router.post("/otp/request", response_model=GenericMessage, tags=["authentication"])
async def request_email_otp(payload: OtpRequest):
    """Generate a 6-digit OTP and email it to the user."""
    try:
        await auth_service.create_and_mail_otp(payload.email, payload.dict())
        return {"message": "OTP sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OTP request error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OTP request")


@router.post("/otp/verify", response_model=GenericMessage, tags=["authentication"])
async def verify_email_otp(payload: OtpVerifyRequest):
    """Verify the 6-digit OTP provided by the user."""
    try:
        await auth_service.verify_otp_and_signup(payload.email, payload.otp)
        return {"message": "OTP verified"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OTP verify error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during OTP verification") 