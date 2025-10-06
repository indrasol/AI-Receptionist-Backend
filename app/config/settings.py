import os
from dotenv import load_dotenv
from pathlib import Path

# First get the environment from ENV variable or default to 'development'
ENV = os.getenv('ENV', 'development')

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load the appropriate .env file based on environment
def load_env_file():
    # First try to load .env.{ENV} file
    env_file = BASE_DIR / f".env.{ENV}"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        # Force override existing environment variables
        load_dotenv(dotenv_path=env_file, override=True)
        return True
    
    # Fallback to the standard .env file
    default_env_file = BASE_DIR / ".env"
    if default_env_file.exists():
        print(f"Loading environment from {default_env_file}")
        # Force override existing environment variables
        load_dotenv(dotenv_path=default_env_file, override=True)
        return True
    
    # If no env file found
    print(f"Warning: No .env.{ENV} or .env file found")
    return False

# Load environment variables
env_file_loaded = load_env_file()

# Print environment for debugging
print(f"Running in {ENV} environment")
if not env_file_loaded:
    print("No .env file found - using environment variables from Azure Key Vault")


# Main
title=os.getenv("title_AIR", "AI Receptionist API")
description=os.getenv("description_AIR", "AI-powered receptionist service for automated call handling")
version=os.getenv("version_AIR", "1.0.0")

SUPABASE_URL=os.getenv("AI_RECEPTION_SUPABASE_URL")
SUPABASE_KEY=os.getenv("AI_RECEPTION_SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY=os.getenv("AI_RECEPTION_SUPABASE_SERVICE_ROLE_KEY")

# Environment-specific Supabase configurations for migrations
SUPABASE_URL_DEV=os.getenv("SUPABASE_URL_DEV")
SUPABASE_ANON_KEY_DEV=os.getenv("SUPABASE_ANON_KEY_DEV")
SUPABASE_URL_PROD=os.getenv("SUPABASE_URL_PROD")
SUPABASE_ANON_KEY_PROD=os.getenv("SUPABASE_ANON_KEY_PROD")
 
SUPABASE_JWT_SECRET=os.getenv("AI_RECEPTION_SUPABASE_JWT_SECRET")
 
VAPI_AUTH_TOKEN=os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
VAPI_ASSISTANT_ID=os.getenv("AI_RECEPTION_VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID=os.getenv("AI_RECEPTION_VAPI_PHONE_NUMBER_ID")
VAPI_WEBHOOK_SECRET=os.getenv('AI_RECEPTION_VAPI_WEBHOOK_SECRET', 'test-secret-12345')

# OpenAI Configuration
CSA_OPENAIIND=os.getenv('CSA_OPENAIIND')

# Chunk generation limits
MAX_TOTAL_CHUNKS_CHARACTERS = int(os.getenv('MAX_TOTAL_CHUNKS_CHARACTERS', '1000000'))  # 1M characters total
MAX_CHUNK_CHARACTERS = int(os.getenv('MAX_CHUNK_CHARACTERS', '100000'))  # 100K characters per chunk
MAX_CHUNKS_PER_URL = int(os.getenv('MAX_CHUNKS_PER_URL', '10'))  # 1 chunk per URL

# Asynchronous task queue (Celery)
REDIS_URL=os.getenv('AI_RECEPTION_REDIS_URL', 'redis://localhost:6379/0')

API_V1_STR=os.getenv('AI_RECEPTION_API_V1_STR', '/api/v1')
HOST=os.getenv('AI_RECEPTION_HOST', '0.0.0.0')
PORT=int(os.getenv('AI_RECEPTION_PORT', '8000'))
LOG_LEVEL=os.getenv('AI_RECEPTION_LOG_LEVEL', 'INFO')
DEBUG=os.getenv('AI_RECEPTION_DEBUG', 'true').lower() in ('true', '1', 'yes', 'on')

# Email settings (used for scrape completion notice)
EMAIL_HOST=os.getenv('EMAIL_HOST')
EMAIL_PORT=int(os.getenv('EMAIL_PORT', '587')) if os.getenv('EMAIL_PORT') else None
EMAIL_USERNAME=os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD=os.getenv('EMAIL_PASSWORD')
EMAIL_FROM=os.getenv('EMAIL_FROM')