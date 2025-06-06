from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Manus AI Clone"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database settings
    database_url: Optional[str] = None
    redis_url: str = "redis://localhost:6379"
    
    # Security settings
    secret_key: str = "dev-secret-key"
    access_token_expire_minutes: int = 30
    
    # Tool settings
    sandbox_enabled: bool = True
    max_execution_time: float = 30.0
    
    class Config:
        env_file = ".env"

settings = Settings()