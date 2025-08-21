# Database functionality removed - using simple console output instead 

from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)

def get_supabase_admin_client() -> Client:
    """Get Supabase client with admin privileges using service role key"""
    if not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for admin operations")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)