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
        """Use Supabase built-in OTP to send verification code."""
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

        # ---------------------------------------------
        # A) Does a user with this email already exist?
        # ---------------------------------------------
        try:
            prof_res = self._supabase.table("profiles").select("email").eq("email", email).single().execute()
            user_exists = bool(prof_res.data)
        except Exception:
            user_exists = False

        if is_signup and user_exists:
            raise ValueError("An account with this email already exists. Please log in instead.")

        if (not is_signup) and (not user_exists):
            raise ValueError("No account found with this email. Please sign up first.")

        # -------------------------------------------------
        # B) Does the organisation name already exist?
        # -------------------------------------------------
        org_exists = False
        if is_signup and norm_meta.get("organization_name"):
            try:
                org_check = self._supabase.table("organizations").select("id").ilike("name", norm_meta["organization_name"]).execute()
                org_exists = bool(org_check.data)
            except Exception:
                org_exists = False

        if is_signup and user_exists is False and org_exists:
            raise ValueError(
                "An account for this organisation already exists. "
                "Ask the admin to invite you, or sign in instead. "
                "If you believe this is an error, contact srvcs@indrasol.com."
            )

        # --------------------------------------------------------------
        # Store user metadata for later use after OTP verification
        # --------------------------------------------------------------
        expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10)).isoformat()
        
        payload = {
            "email": email,
            "expires_at": expires_at,
        }

        if is_signup and isinstance(norm_meta, dict):
            for field in ("organization_name", "first_name", "last_name"):
                value = norm_meta.get(field)
                if value:
                    payload[field] = value

        # Store metadata in email_otps table (we'll use this after verification)
        self._supabase.table("email_otps").upsert(payload).execute()

        # --------------------------------------------------------------
        # Use Supabase built-in OTP sending
        # --------------------------------------------------------------
        try:
            # Use Supabase Auth API to send OTP
            response = requests.post(
                f"{self.auth_url}/otp",
                headers=self._get_auth_headers(),
                json={
                    "email": email,
                    "options": {
                        "email_redirect_to": None  # Optional: redirect URL after verification
                    }
                }
            )
            
            # Debug logging
            logger.info(f"Supabase OTP send response status: {response.status_code}")
            logger.info(f"Supabase OTP send response content: {response.text[:500]}")  # First 500 chars
            
            if not response.ok:
                try:
                    error_detail = response.json() if response.content else response.text
                except:
                    error_detail = response.text
                logger.error(f"Supabase OTP sending failed: {error_detail}")
                raise ValueError(f"Failed to send OTP: {error_detail}")
                
            logger.info(f"OTP sent successfully to {email}")
            
        except Exception as e:
            logger.error(f"Error sending OTP via Supabase: {str(e)}")
            raise ValueError(f"Failed to send verification code: {str(e)}")

    async def verify_otp_and_signup(self, email: str, code: str):
        """Verify OTP with Supabase and complete signup/login process."""
        import datetime as dt

        # --------------------------------------------------------------
        # Verify OTP with Supabase Auth API
        # --------------------------------------------------------------
        try:
            # Use Supabase Auth API to verify OTP
            # The correct endpoint is /verify for OTP verification
            response = requests.post(
                f"{self.auth_url}/verify",
                headers=self._get_auth_headers(),
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
        # Get stored metadata from email_otps table
        # --------------------------------------------------------------
        try:
            res = self._supabase.table("email_otps").select("*").eq("email", email).single().execute()
            row = res.data if res.data else None
            
            if not row:
                raise ValueError("OTP session not found or expired")
                
            # Check if metadata has expired
            now_utc = dt.datetime.now(dt.timezone.utc)
            expires_at = dt.datetime.fromisoformat(row["expires_at"])
            
            # If Supabase returned a naive datetime (unlikely), assume UTC
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
                
            if now_utc > expires_at:
                raise ValueError("OTP session expired")
                
        except Exception as e:
            logger.error(f"Error retrieving OTP metadata: {str(e)}")
            raise ValueError("OTP session not found or expired")

        # Clean up OTP metadata
        self._supabase.table("email_otps").delete().eq("email", email).execute()

        # --------------------------------------------------------------
        # Complete signup/login process
        # --------------------------------------------------------------
        org_name = row.get("organization_name")
        first_name = row.get("first_name")
        last_name = row.get("last_name")
        
        # Determine if this is a signup or login flow
        is_signup = any([org_name, first_name, last_name])
        
        if is_signup:
            # This is a signup flow - create user profile and organization
            await self._complete_signup_process(email, org_name, first_name, last_name)
        else:
            # This is a login flow - just verify the user exists
            await self._complete_login_process(email)

        # Generate JWT token for the user
        token_data = await self._generate_user_tokens(email)
        
        return token_data

    async def _complete_signup_process(self, email: str, org_name: str, first_name: str, last_name: str):
        """Complete the signup process by creating user profile and organization."""
        import datetime as dt
        try:
            # Create organization if it doesn't exist
            org_id = await self._get_or_create_organization(org_name)
            
            # Create user profile
            profile_payload = {
                "email": email,
                "organization_id": org_id,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": datetime.now(dt.timezone.utc).isoformat(),
                "updated_at": datetime.now(dt.timezone.utc).isoformat()
            }
            
            self._supabase.table("profiles").insert(profile_payload).execute()
            logger.info(f"User profile created for {email}")
            
        except Exception as e:
            logger.error(f"Error completing signup process: {str(e)}")
            raise ValueError("Failed to complete signup process")

    async def _complete_login_process(self, email: str):
        """Complete the login process by verifying user exists."""
        try:
            # Verify user profile exists
            prof_res = self._supabase.table("profiles").select("email").eq("email", email).single().execute()
            if not prof_res.data:
                raise ValueError("User profile not found")
                
            logger.info(f"Login verified for {email}")
            
        except Exception as e:
            logger.error(f"Error completing login process: {str(e)}")
            raise ValueError("Failed to complete login process")

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

    async def _get_or_create_organization(self, org_name: str):
        """Get existing organization or create new one."""
        import datetime as dt
        try:
            if not org_name:
                return None
                
            # Check if organization already exists
            org_res = self._supabase.table("organizations").select("id").eq("name", org_name).execute()
            if org_res.data and len(org_res.data) > 0:
                return org_res.data[0]["id"]
            
            # Create new organization
            org_payload = {
                "name": org_name,
                "created_at": datetime.now(dt.timezone.utc).isoformat(),
                "updated_at": datetime.now(dt.timezone.utc).isoformat()
            }
            org_result = self._supabase.table("organizations").insert(org_payload).execute()
            return org_result.data[0]["id"] if org_result.data else None
            
        except Exception as e:
            logger.error(f"Error handling organization: {str(e)}")
            return None
    
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