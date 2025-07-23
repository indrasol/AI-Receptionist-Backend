import os
from pydantic import BaseModel

# No .env or AZURE_ENV logic; use only os.getenv

class Settings(BaseModel):
    app_name: str = os.getenv('APP_NAME', 'AI Receptionist API')
    debug: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    api_v1_str: str = os.getenv('API_V1_STR', '/api/v1')
    host: str = os.getenv('HOST', '0.0.0.0')
    port: int = int(os.getenv('PORT', '8000'))
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    supabase_url: str = os.getenv('SUPABASE_URL', '')
    supabase_key: str = os.getenv('SUPABASE_KEY', '')

settings = Settings()

# Debug print for troubleshooting
print(f"DEBUG env: {os.getenv('DEBUG')}")
print(f"settings.debug: {settings.debug}")