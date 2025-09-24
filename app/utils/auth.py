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

        # Get user's organization information
        try:
            from app.database_operations import get_user_organization, ensure_user_organization
            
            # Get user's organization from metadata (pass claims for efficiency)
            user_org = await get_user_organization(user.get('claims').get('sub'), user.get('claims'))
            if not user_org:
                raise HTTPException(status_code=400, detail="User has no organization configured")
            
            # Add organization info to user claims
            if user_org:
                user['claims']['organization'] = user_org
                logger.info(f"User {user.get('claims').get('email')} belongs to organization: {user_org.get('name')}")
            else:
                logger.warning(f"Could not determine organization for user {user.get('claims').get('email')}")
                
        except Exception as org_error:
            logger.error(f"Error getting user organization: {str(org_error)}")
            # Don't fail authentication if organization lookup fails

        return user.get('claims')
        
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token. Please sign in again. Authentication failed: {str(e)}"
        )
