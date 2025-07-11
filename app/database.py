# Database functionality removed - using simple console output instead 

from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_key)