import os
import requests
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.config.settings import SUPABASE_JWT_SECRET
from app.schemas.auth import UserSignupRequest, UserSigninRequest, UserResponse, AuthResponse
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Service class for handling authentication operations"""
    
    def __init__(self):
        self.supabase_url = os.getenv("AI_RECEPTION_SUPABASE_URL")
        self.supabase_key = os.getenv("AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY")
        self.supabase_anon_key = os.getenv("AI_RECEPTION_SUPABASE_KEY")  # Anon key from env
        self.supabase_jwt_secret = os.getenv("AI_RECEPTION_SUPABASE_JWT_SECRET")
        self.auth_url = f"{self.supabase_url}/auth/v1"
        
        # Validate required environment variables
        if not all([self.supabase_url, self.supabase_key, self.supabase_jwt_secret]):
            raise RuntimeError(
                "Missing required environment variables: "
                "AI_RECEPTION_SUPABASE_URL, AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY, "
                "AI_RECEPTION_SUPABASE_JWT_SECRET"
            )
        
        # Supabase client for OTP table operations
        from app.database_operations import get_supabase_client  # local import to avoid circular
        self._supabase = get_supabase_client()
    
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
            
            # Get default organization ID (CSA)
            default_org_id = await self._get_default_organization_id()
            
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
                        "last_name": user_data.last_name,
                        "organization_id": default_org_id,
                        "organization_name": "CSA"
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
                created_at=user_info.get("created_at", datetime.now(dt.timezone.utc).isoformat()),
                updated_at=user_info.get("updated_at", datetime.now(dt.timezone.utc).isoformat())
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
                created_at=user.get("created_at", datetime.now(dt.timezone.utc).isoformat()),
                updated_at=user.get("updated_at", datetime.now(dt.timezone.utc).isoformat())
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
                audience="authenticated",
                leeway=10,
                options={"verify_iat": False},  # ignore minimal clock skew issues
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

    # ------------------------------------------------------------------
    # OTP signup helpers
    # ------------------------------------------------------------------

    async def create_and_mail_otp(self, email: str, user_meta: dict):
        """Use Supabase built-in OTP to send verification code with metadata."""
        import datetime as dt

        # --------------------------------------------------------------
        # Determine flow (signup vs login) based on presence of metadata
        # --------------------------------------------------------------
        norm_meta = user_meta or {}
        # Support camelCase keys from frontend
        if "organizationName" in norm_meta and not norm_meta.get("organization_name"):
            norm_meta["organization_name"] = norm_meta["organizationName"]

        if "firstName" in norm_meta and not norm_meta.get("first_name"):
            norm_meta["first_name"] = norm_meta["firstName"]

        if "lastName" in norm_meta and not norm_meta.get("last_name"):
            norm_meta["last_name"] = norm_meta["lastName"]

        is_signup = any(norm_meta.get(k) for k in ("organization_name", "first_name", "last_name"))

        # -------------------------------------------------
        # Check if organisation name already exists (for signup)
        # Supabase Auth handles email uniqueness automatically!
        # -------------------------------------------------
        org_exists = False
        if is_signup and norm_meta.get("organization_name"):
            try:
                org_check = self._supabase.table("organizations").select("id").ilike("name", norm_meta["organization_name"]).execute()
                org_exists = bool(org_check.data)
            except Exception:
                org_exists = False

        if is_signup and org_exists:
            raise ValueError(
                "An account for this organisation already exists. "
                "Ask the admin to invite you, or sign in instead. "
                "If you believe this is an error, contact srvcs@indrasol.com."
            )

        # --------------------------------------------------------------
        # Send OTP with metadata - let Supabase handle user creation
        # The metadata will be stored when OTP is verified
        # --------------------------------------------------------------
        try:
            # Prepare metadata for signup flows
            signup_data = None
            if is_signup:
                signup_data = {
                    "organization_name": norm_meta.get("organization_name"),
                    "first_name": norm_meta.get("first_name"),
                    "last_name": norm_meta.get("last_name"),
                    "signup_flow": True  # Flag for trigger
                }
            
            logger.info(f"Sending OTP to {email} with data: {signup_data}")
            
            # Send OTP with metadata - Supabase will store it
            otp_response = requests.post(
                f"{self.auth_url}/otp",
                headers={
                    "apikey": self.supabase_anon_key,
                    "Content-Type": "application/json"
                },
                json={
                    "email": email,
                    "data": signup_data,  # This stores metadata
                    "options": {
                        "email_redirect_to": None  # No redirect link
                    }
                }
            )
            
            logger.info(f"Supabase OTP response: {otp_response.status_code} - {otp_response.text[:200]}")
            
            if not otp_response.ok:
                error_detail = otp_response.json() if otp_response.content else otp_response.text
                logger.error(f"Supabase OTP failed: {error_detail}")
                raise ValueError(f"Failed to send OTP: {error_detail}")
                
            logger.info(f"OTP sent successfully to {email}")
            
        except Exception as e:
            logger.error(f"Error sending OTP: {str(e)}")
            raise ValueError(f"Failed to send verification code: {str(e)}")

    async def verify_otp_and_signup(self, email: str, code: str):
        """Verify OTP with Supabase - trigger handles profile/org creation automatically."""
        import datetime as dt

        # --------------------------------------------------------------
        # Verify OTP with Supabase Auth API
        # This will update confirmed_at timestamp when OTP is verified
        # Database trigger will fire and create profile & organization
        # --------------------------------------------------------------
        try:
            # Use Supabase Auth API to verify OTP
            # This endpoint updates confirmed_at when OTP is correct
            response = requests.post(
                f"{self.auth_url}/verify",
                headers={
                    "apikey": self.supabase_anon_key,  # Use anon key for verification too
                    "Content-Type": "application/json"
                },
                json={
                    "email": email,
                    "token": code,
                    "type": "email"
                }
            )
            
            # Debug logging
            logger.info(f"Supabase OTP verify response status: {response.status_code}")
            logger.info(f"Supabase OTP verify response content: {response.text[:500]}")  # First 500 chars
            
            if not response.ok:
                try:
                    error_detail = response.json() if response.content else response.text
                except:
                    error_detail = response.text
                logger.error(f"Supabase OTP verification failed: {error_detail}")
                raise ValueError("Invalid or expired OTP code")
            
            # Try to parse JSON response
            try:
                auth_data = response.json()
                logger.info(f"OTP verified successfully for {email}")
            except Exception as json_error:
                logger.error(f"Failed to parse Supabase response as JSON: {json_error}")
                logger.error(f"Raw response: {response.text}")
                # If it's not JSON, it might be a successful response with different format
                if response.status_code == 200:
                    auth_data = {"success": True}
                    logger.info(f"OTP verified successfully for {email} (non-JSON response)")
                else:
                    raise ValueError("Invalid or expired OTP code")
            
        except Exception as e:
            logger.error(f"Error verifying OTP via Supabase: {str(e)}")
            raise ValueError("Invalid or expired OTP code")

        # --------------------------------------------------------------
        # At this point:
        # 1. Supabase has created the user with metadata (for signup)
        # 2. Database trigger has created profile & organization (for signup)
        # 3. For login, user already exists, no trigger action needed
        # --------------------------------------------------------------

        # Generate JWT token for the user
        token_data = await self._generate_user_tokens(email)
        
        return token_data


    async def _generate_user_tokens(self, email: str):
        """Generate JWT tokens for the authenticated user."""
        import datetime as dt
        try:
            # Get user profile for token generation
            prof_res = self._supabase.table("profiles").select("*").eq("email", email).single().execute()
            profile = prof_res.data if prof_res.data else {}
            
            # Generate JWT token
            token_payload = {
                "sub": email,
                "email": email,
                "user_id": profile.get("id"),
                "organization_id": profile.get("organization_id"),
                "exp": datetime.now(dt.timezone.utc) + timedelta(hours=24),
                "iat": datetime.now(dt.timezone.utc),
                "aud": "authenticated"  # Required audience claim for Supabase
            }
            
            token = jwt.encode(token_payload, self.supabase_jwt_secret, algorithm="HS256")
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": 86400,  # 24 hours
                "user": {
                    "email": email,
                    "first_name": profile.get("first_name"),
                    "last_name": profile.get("last_name"),
                    "organization_id": profile.get("organization_id")
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating user tokens: {str(e)}")
            raise ValueError("Failed to generate authentication tokens")

    
    async def _get_default_organization_id(self) -> str:
        """Get the default organization ID (CSA)"""
        try:
            # Import here to avoid circular imports
            from app.database_operations import get_supabase_client
            
            supabase = get_supabase_client()
            org_result = supabase.table("organizations").select("id").eq("name", "CSA").execute()
            
            if not org_result.data:
                logger.error("CSA organization not found in database")
                raise ValueError("Default organization not found")
            
            return org_result.data[0]["id"]
            
        except Exception as e:
            logger.error(f"Failed to get default organization ID: {str(e)}")
            raise ValueError("Failed to get default organization")