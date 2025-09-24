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

    # ------------------------------------------------------------------
    # OTP signup helpers
    # ------------------------------------------------------------------

    async def create_and_mail_otp(self, email: str, user_meta: dict):
        """Generate 6-digit OTP, store its hash, and email the code."""
        import secrets, hashlib, datetime as dt

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

        # Check whether user already exists in profiles
        try:
            prof_res = self._supabase.table("profiles").select("email").eq("email", email).single().execute()
            user_exists = bool(prof_res.data)
        except Exception:
            user_exists = False  # profiles table may not exist yet

        if is_signup and user_exists:
            raise ValueError("Account already exists. Please log in instead.")

        if (not is_signup) and (not user_exists):
            raise ValueError("No account found. Please sign up first.")

        # --------------------------------------------------------------
        # Generate and store OTP
        # --------------------------------------------------------------
        code = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = hashlib.sha256(code.encode()).hexdigest()
        expires_at = (dt.datetime.utcnow() + dt.timedelta(minutes=10)).isoformat()

        payload = {
            "email": email,
            "otp_hash": otp_hash,
            "expires_at": expires_at,
        }

        if is_signup and isinstance(norm_meta, dict):
            for field in ("organization_name", "first_name", "last_name"):
                value = norm_meta.get(field)
                if value:
                    payload[field] = value

        self._supabase.table("email_otps").upsert(payload).execute()

        # Send the e-mail (include first_name if provided)
        first_name = norm_meta.get("first_name") if isinstance(norm_meta, dict) else None
        client_ip = norm_meta.get("client_ip") if isinstance(norm_meta, dict) else None
        self._send_email(email, code, first_name=first_name, client_ip=client_ip)

    async def verify_otp_and_signup(self, email: str, code: str):
        """Validate OTP; on success delete it (extend here to create user)."""
        import hashlib, datetime as dt

        hash_check = hashlib.sha256(code.encode()).hexdigest()
        res = self._supabase.table("email_otps").select("*").eq("email", email).single().execute()
        row = res.data if res.data else None

        if not row or row["otp_hash"] != hash_check:
            raise ValueError("Invalid OTP")

        # Ensure both datetimes are timezone-aware (UTC) to avoid comparison errors
        now_utc = dt.datetime.now(dt.timezone.utc)
        expires_at = dt.datetime.fromisoformat(row["expires_at"])

        # If Supabase returned a naive datetime (unlikely), assume UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.timezone.utc)

        if now_utc > expires_at:
            raise ValueError("OTP expired")

        # Clean up
        self._supabase.table("email_otps").delete().eq("email", email).execute()

        # TODO: progress signup or mark verified

        # ------------------------------------------------------------------
        # Persist user profile
        # ------------------------------------------------------------------
        org_name = row.get("organization_name")
        first_name = row.get("first_name")
        last_name = row.get("last_name")

        profile_payload = {
            "email": email,
            "organization_name": org_name,
            "first_name": first_name,
            "last_name": last_name,
        }

        # If organization table exists, fetch or create row
        try:
            if org_name:
                org_res = self._supabase.table("organizations").select("id").ilike("name", org_name).execute()
                if org_res.data and len(org_res.data) > 0:
                    org_id = org_res.data[0]["id"]
                else:
                    # Insert new organization
                    print(org_name, "Inserting new organization")
                    insert_res = self._supabase.table("organizations").insert({"name": org_name}).execute()
                    org_id = insert_res.data[0]["id"] if (insert_res.data and len(insert_res.data) > 0) else None
 
                if org_id:
                    profile_payload["organization_id"] = org_id
        except Exception as e:
            logger.warning(f"Organization fetch/create failed: {e}")

        # Upsert profile row keyed by email (initial, without user_id yet)
        self._supabase.table("profiles").upsert(profile_payload, on_conflict="email").execute()

        # ------------------------------------------------------------------
        # Ensure Supabase auth.users has the same metadata
        # ------------------------------------------------------------------
        try:
            # Look for existing auth user
            auth_user = await self._find_user_by_email(email)

            if not auth_user:
                # Create a new auth user with confirmed email & metadata
                import requests, secrets, string

                random_pwd = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

                create_res = requests.post(
                    f"{self.auth_url}/admin/users",
                    headers=self._get_auth_headers(),
                    json={
                        "email": email,
                        "password": random_pwd,
                        "email_confirm": True,
                        "user_metadata": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "organization_id": profile_payload.get("organization_id"),
                            "organization_name": org_name,
                            "signup_flow": True,
                        },
                    },
                )

                if not create_res.ok:
                    logger.warning(f"Failed to create auth user: {create_res.text}")
                else:
                    auth_user = create_res.json()

            else:
                # Update existing metadata
                user_id = auth_user["id"] if isinstance(auth_user, dict) else auth_user.get("id")

                if user_id:
                    import requests

                    requests.put(
                        f"{self.auth_url}/admin/users/{user_id}",
                        headers=self._get_auth_headers(),
                        json={
                            "user_metadata": {
                                "first_name": first_name,
                                "last_name": last_name,
                                "organization_id": profile_payload.get("organization_id"),
                                "organization_name": org_name,
                                "signup_flow": True,
                            }
                        },
                    )
        except Exception as e:
            logger.warning(f"Failed to sync auth.users metadata: {e}")

        # ------------------------------------------------------------------
        # Update profiles with user_id now that we have auth_user
        # ------------------------------------------------------------------

        try:
            if auth_user and isinstance(auth_user, dict):
                user_id_val = auth_user.get("id")
                if user_id_val:
                    self._supabase.table("profiles").update({"user_id": user_id_val}).eq("email", email).execute()
        except Exception as e:
            logger.warning(f"Failed to set user_id in profiles: {e}")

        # ------------------------------------------------------------------
        # Issue JWT for the newly verified user
        # ------------------------------------------------------------------
        token = self._generate_jwt({
            "sub": email,
            "email": email,
            "user_metadata": {
                "first_name": first_name,
                "last_name": last_name,
                "organization_id": profile_payload.get("organization_id"),
                "organization_name": org_name,
            }
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 24 * 3600,
        }

    # ------------------------------------------------------------------
    # JWT helper
    # ------------------------------------------------------------------

    def _generate_jwt(self, claims: dict, *, expires_in_sec: int = 24 * 3600) -> str:
        """Generate a signed JWT using the Supabase JWT secret."""
        import jwt, datetime as dt, os

        now = dt.datetime.utcnow()
        payload = {
            **claims,
            "iat": int(now.timestamp()),
            "exp": int((now + dt.timedelta(seconds=expires_in_sec)).timestamp()),
            "aud": "authenticated",
        }

        secret = os.getenv("AI_RECEPTION_SUPABASE_JWT_SECRET", self.supabase_jwt_secret)
        return jwt.encode(payload, secret, algorithm="HS256")

    # ------------------------------------------------------------------
    # E-mail sending (Office 365 / Outlook SMTP)
    # ------------------------------------------------------------------

    def _send_email(self, to_email: str, code: str, *, first_name: str | None = None, client_ip: str | None = None):
        """Send OTP email with both plain-text and HTML parts."""
        import smtplib, ssl, os, datetime as dt
        from email.message import EmailMessage

        product = os.getenv("PRODUCT_NAME", "AI Receptionist By Indrasol")
        expire_minutes = 10
        request_time = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        subject = f"Your {product} verification code"

        preheader = f"Enter this code to continue. Expires in {expire_minutes} minutes."

        # ---------- Plain-text fallback ----------
        text = (
            f"Hi{f' {first_name}' if first_name else ''},\n\n"
            f"Your one-time verification code is: {code}\n\n"
            f"It expires in {expire_minutes} minutes and can be used only once.\n"
            f"Only enter this code in {product}. We'll never ask for it by phone or chat.\n\n"
            f"Request details: {request_time}, IP {client_ip or 'Unknown'}\n"
            "If this wasn’t you, just ignore this email or contact support@indrasol.com.\n\n"
            f"— {product}"
        )

        # ---------- HTML version ----------
        html = f"""\
<!doctype html>
<html>
  <body style=\"margin:0;padding:0;background:#f6f7f9;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;\">
    <span style=\"display:none!important;opacity:0;color:transparent;height:0;width:0;overflow:hidden;\">
      {preheader}
    </span>
    <div style=\"max-width:560px;margin:40px auto;background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.06)\">
      <h2 style=\"margin:0 0 12px;font-weight:700;\">Your verification code</h2>
      <p style=\"margin:0 0 18px;color:#444\">Use this code to continue signing in to <strong>{product}</strong>.</p>
      <div style=\"font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size:28px;letter-spacing:4px;font-weight:800;padding:14px 16px; border:1px solid #e7e9ee;border-radius:10px;text-align:center;\">
        {code}
      </div>
      <p style=\"margin:18px 0 8px;color:#444\">This code expires in <strong>{expire_minutes} minutes</strong> and can be used once.</p>
      <p style=\"margin:0 0 18px;color:#444\">Only enter this code in {product}. We’ll never ask for it by phone or chat.</p>
      <hr style=\"border:none;border-top:1px solid #eee;margin:18px 0\">
      <p style=\"margin:0;color:#6b7280;font-size:12px;\">
        Didn’t request this? Ignore this email or contact <a href=\"mailto:srvcs@indrasol.com\">srvcs@indrasol.com</a>.
      </p>
    </div>
    <div style=\"text-align:center;color:#9aa0a6;font-size:12px;margin:12px 0;\">
      © {dt.datetime.utcnow().year} {product}
    </div>
  </body>
</html>
"""

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.getenv("EMAIL_FROM")
        msg["To"] = to_email
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")

        host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        port = int(os.getenv("EMAIL_PORT", "587"))
        user = os.getenv("EMAIL_USERNAME")
        pwd = os.getenv("EMAIL_PASSWORD")

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            server.login(user, pwd)
            server.send_message(msg)
    
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