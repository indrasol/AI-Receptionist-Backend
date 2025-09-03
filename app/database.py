from supabase import create_client, Client
from app.config.settings import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY
from fastapi import HTTPException
from functools import lru_cache
import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def log_debugger(message: str):
    """Helper function for debug logging"""
    logger.debug(message)


# Global thread pool for running Supabase operations asynchronously
thread_pool = ThreadPoolExecutor()

# Initialize Supabase client
@lru_cache
def get_supabase_client():
    # Prefer service role key on the server for privileged operations (e.g., storage uploads)
    # Fallback to public anon key if service key is not configured
    key_to_use = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    log_debugger(f"SUPABASE_URL: {SUPABASE_URL}")
    # Avoid logging the actual secret value
    which_key = "anon" if SUPABASE_KEY else "service"
    log_debugger(f"Using Supabase key type: {which_key}")
    supbase: Client = create_client(SUPABASE_URL, key_to_use)
    return supbase

# Helper to run Supabase operations asynchronously
async def run_supabase_async(func):
    return await asyncio.get_event_loop().run_in_executor(
        thread_pool, func
    )

# Helper for safer Supabase operations with error handling
async def safe_supabase_operation(operation, error_message="Supabase operation failed", retries: int = 3, backoff_seconds: float = 0.25):
    attempt = 0
    while True:
        try:
            return await run_supabase_async(operation)
        except Exception as e:
            attempt += 1
            error_text = str(e)
            is_transient = (
                "RemoteProtocolError" in error_text or
                "ConnectionResetError" in error_text or
                "StreamClosed" in error_text or
                "ConnectionTerminated" in error_text
            )
            if attempt <= retries and is_transient:
                await asyncio.sleep(backoff_seconds * attempt)
                continue
            raise HTTPException(status_code=500, detail=f"{error_message}: {error_text}")
