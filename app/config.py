from typing import List
import os
from pydantic import BaseModel, validator


class Settings(BaseModel):
    # FastAPI Configuration
    app_name: str = "AI Receptionist API"
    debug: bool = True
    api_v1_str: str = "/api/v1"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Configuration
    backend_cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    log_level: str = "INFO"
    
    # Supabase Configuration
    supabase_url: str = ""
    supabase_key: str = ""
    
    @validator("backend_cors_origins", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


# Load environment variables
def load_env_file():
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env_vars

def parse_cors_origins(cors_str):
    """Parse CORS origins from string to list"""
    if not cors_str:
        return ["http://localhost:3000", "http://localhost:8080"]
    
    # Remove brackets and split by comma
    cors_str = cors_str.strip('[]')
    if not cors_str:
        return ["http://localhost:3000", "http://localhost:8080"]
    
    # Split by comma and clean up each URL
    origins = [origin.strip().strip('"').strip("'") for origin in cors_str.split(',')]
    return [origin for origin in origins if origin]

# Create settings instance with environment variables
env_vars = load_env_file()
settings = Settings(
    app_name=env_vars.get('APP_NAME', 'AI Receptionist API'),
    debug=env_vars.get('DEBUG', 'True').lower() == 'true',
    api_v1_str=env_vars.get('API_V1_STR', '/api/v1'),
    host=env_vars.get('HOST', '0.0.0.0'),
    port=int(env_vars.get('PORT', '8000')),
    backend_cors_origins=parse_cors_origins(env_vars.get('BACKEND_CORS_ORIGINS')),
    log_level=env_vars.get('LOG_LEVEL', 'INFO'),
    supabase_url=env_vars.get('SUPABASE_URL', ''),
    supabase_key=env_vars.get('SUPABASE_KEY', '')
) 