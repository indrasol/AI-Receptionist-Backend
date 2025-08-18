"""
Common authentication utilities for the AI Receptionist API
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for token extraction
http_bearer = HTTPBearer()

async def get_current_user(authorization: str = Depends(http_bearer)):
    """
    Common authentication dependency for all protected endpoints
    
    Args:
        authorization: HTTPBearer dependency that extracts the Authorization header
        
    Returns:
        dict: User information from the verified JWT token
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or missing
    """
    try:
        # Extract token from Authorization header
        token = AuthService.get_token_from_header(authorization.credentials)

        # Verify the token
        auth_service = AuthService()
        user = await auth_service.verify_token(token)

        logger.info(f"User authenticated: {user.get('claims').get('email', 'unknown')}")

        return user.get('claims')
        
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token. Please sign in again. Authentication failed: {str(e)}"
        )
