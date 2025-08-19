import os
import requests
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.config import settings
from app.schemas.auth import UserSignupRequest, UserSigninRequest, UserResponse, AuthResponse
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Service class for handling authentication operations"""
    
    def __init__(self):
        self.supabase_url = os.getenv("AI_RECEPTION_SUPABASE_URL")
        self.supabase_key = os.getenv("AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY")
        self.supabase_jwt_secret = os.getenv("AI_RECEPTION_SUPABASE_JWT_SECRET")
        self.auth_url = f"{self.supabase_url}/auth/v1"
        
        # Validate required environment variables
        if not all([self.supabase_url, self.supabase_key, self.supabase_jwt_secret]):
            raise RuntimeError(
                "Missing required environment variables: "
                "AI_RECEPTION_SUPABASE_URL, AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY, "
                "AI_RECEPTION_SUPABASE_JWT_SECRET"
            )
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers for Supabase auth API calls"""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
    
    async def signup_user(self, user_data: UserSignupRequest) -> UserResponse:
        """Register a new user"""
        try:
            # Check if username already exists
            existing_user = await self._find_user_by_username(user_data.username)
            if existing_user:
                raise ValueError(f"Username '{user_data.username}' already exists")
            
            # Check if email already exists
            existing_email = await self._find_user_by_email(user_data.email)
            if existing_email:
                raise ValueError(f"Email '{user_data.email}' already exists")
            
            # Create user in Supabase
            response = requests.post(
                f"{self.auth_url}/admin/users",
                headers=self._get_auth_headers(),
                json={
                    "email": user_data.email,
                    "password": user_data.password,
                    "email_confirm": True,  # Auto-confirm email
                    "user_metadata": {
                        "username": user_data.username,
                        "first_name": user_data.first_name,
                        "last_name": user_data.last_name
                    }
                }
            )
            
            if not response.ok:
                error_detail = response.json() if response.content else response.text
                logger.error(f"Supabase signup failed: {error_detail}")
                raise ValueError(f"Failed to create user: {error_detail}")
            
            user_info = response.json()
            
            # Return user data
            return UserResponse(
                id=user_info["id"],
                email=user_info["email"],
                username=user_data.username,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                created_at=user_info.get("created_at", datetime.utcnow().isoformat()),
                updated_at=user_info.get("updated_at", datetime.utcnow().isoformat())
            )
            
        except Exception as e:
            logger.error(f"Signup failed: {str(e)}")
            raise
    
    async def signin_user(self, credentials: UserSigninRequest) -> AuthResponse:
        """Authenticate user and return tokens"""
        try:
            identifier = credentials.identifier
            password = credentials.password
            # Determine if identifier is email or username
            if "@" in identifier:
                email = identifier
            else:
                # Find user by username
                user = await self._find_user_by_username(identifier)
                if not user:
                    raise ValueError("Invalid username or password")
                email = user["email"]
            
            # Authenticate with Supabase
            response = requests.post(
                f"{self.auth_url}/token?grant_type=password",
                headers={"apikey": self.supabase_key},
                json={
                    "email": email,
                    "password": password
                }
            )
            
            if not response.ok:
                error_detail = response.json() if response.content else response.text
                logger.error(f"Supabase signin failed: {error_detail}")
                raise ValueError("Invalid username or password")
            
            auth_data = response.json()
            # Get user details
            user = await self._find_user_by_email(email)
            print(user)
            if not user:
                raise ValueError("User not found")
            
            # Create user response
            user_response = UserResponse(
                id=user["id"],
                email=user["email"],
                username=user.get("user_metadata", {}).get("username", ""),
                first_name=user.get("user_metadata", {}).get("first_name"),
                last_name=user.get("user_metadata", {}).get("last_name"),
                created_at=user.get("created_at", datetime.utcnow().isoformat()),
                updated_at=user.get("updated_at", datetime.utcnow().isoformat())
            )
            
            # Create auth response
            return AuthResponse(
                access_token=auth_data["access_token"],
                refresh_token=auth_data["refresh_token"],
                token_type="bearer",
                expires_in=auth_data.get("expires_in", 3600),
                user=user_response
            )
        except Exception as e:
            logger.error(f"Signin failed: {str(e)}")
            raise
    
    async def logout_user(self, refresh_token: str) -> bool:
        """Logout user by invalidating refresh token"""
        try:
            response = requests.post(
                f"{self.auth_url}/logout",
                headers={"apikey": self.supabase_key},
                json={"refresh_token": refresh_token}
            )
            
            if not response.ok:
                logger.warning(f"Logout request failed: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims"""
        try:
            # Add debug logging
            logger.info(f"Attempting to verify token: {token[:20]}...")
            logger.info(f"Using JWT secret: {self.supabase_jwt_secret[:10]}...")
            
            decoded = jwt.decode(
                token, 
                self.supabase_jwt_secret, 
                algorithms=["HS256"],
                audience="authenticated"  # Supabase expects this audience
            )
            logger.info(f"Token verified successfully, claims: {decoded}")
            return {"valid": True, "claims": decoded}
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return {"valid": False, "message": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return {"valid": False, "message": f"Invalid token: {str(e)}"}
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return {"valid": False, "message": f"Token verification failed: {str(e)}"}
    
    async def reset_password(self, email: str) -> bool:
        """Send password reset email"""
        try:
            response = requests.post(
                f"{self.auth_url}/recover",
                headers={"apikey": self.supabase_key},
                json={"email": email}
            )
            
            if not response.ok:
                logger.error(f"Password reset failed: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            return False
    
    async def _find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find user by username"""
        try:
            response = requests.get(
                f"{self.auth_url}/admin/users",
                headers=self._get_auth_headers()
            )
            
            if not response.ok:
                logger.warning(f"Failed to fetch users: {response.status_code} - {response.text}")
                return None
            
            # Parse response only once and handle potential errors
            try:
                users = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse users response as JSON: {json_error}")
                logger.error(f"Response content: {response.text}")
                return None
            
            # Handle both list and dict responses from Supabase
            if isinstance(users, dict):
                # If it's a dict, it might be an error response or single user
                if "error" in users or "message" in users:
                    logger.error(f"Supabase API error: {users}")
                    return None
                
                # Check if it's the new format with 'users' key
                if "users" in users and isinstance(users["users"], list):
                    # Extract the actual users list
                    actual_users = users["users"]
                    for user in actual_users:
                        if isinstance(user, dict) and user.get("user_metadata", {}).get("username") == username:
                            return user
                    return None
                
                # If it's a single user object, check if it matches
                if users.get("user_metadata", {}).get("username") == username:
                    return users
                return None
            elif isinstance(users, list):
                # Normal case: list of users
                for user in users:
                    if isinstance(user, dict) and user.get("user_metadata", {}).get("username") == username:
                        return user
            else:
                logger.error(f"Unexpected response type from Supabase: {type(users)}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by username: {str(e)}")
            return None
    
    async def _find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        try:
            response = requests.get(
                f"{self.auth_url}/admin/users",
                headers=self._get_auth_headers()
            )
            
            if not response.ok:
                logger.warning(f"Failed to fetch users: {response.status_code} - {response.text}")
                return None
            
            # Parse response only once and handle potential errors
            try:
                users = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse users response as JSON: {json_error}")
                logger.error(f"Response content: {response.text}")
                return None
            print(isinstance(users, list))
            print(users)
            print(isinstance(users, dict))
            print(users)
            # Handle both list and dict responses from Supabase
            if isinstance(users, dict):
                # If it's a dict, it might be an error response or single user
                if "error" in users or "message" in users:
                    logger.error(f"Supabase API error: {users}")
                    return None
                
                # Check if it's the new format with 'users' key
                if "users" in users and isinstance(users["users"], list):
                    # Extract the actual users list
                    actual_users = users["users"]
                    for user in actual_users:
                        if isinstance(user, dict) and user.get("email") == email:
                            return user
                    return None
                
                # If it's a single user object, check if it matches
                if users.get("email") == email:
                    return users
                return None
            elif isinstance(users, list):
                # Normal case: list of users
                for user in users:
                    if isinstance(user, dict) and user.get("email") == email:
                        return user
            else:
                logger.error(f"Unexpected response type from Supabase: {type(users)}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by email: {str(e)}")
            return None
    
    @staticmethod
    def get_token_from_header(authorization: str) -> str:
        """
        Extract JWT token from Authorization header
        
        Args:
            authorization: Authorization header value (e.g., "Bearer <token>")
            
        Returns:
            JWT token string
            
        Raises:
            HTTPException: If token is missing or invalid format
        """
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is required"
            )
        
        token = authorization[:]
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Token is missing from authorization header"
            )
            
        return token 