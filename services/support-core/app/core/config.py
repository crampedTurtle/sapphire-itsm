"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://sapphire:sapphire@postgres.home.lan:5432/sapphire_support"
    
    # AI Gateway
    AI_GATEWAY_URL: str = "http://vm-ai2:8080"
    AI_GATEWAY_API_KEY: str = ""
    
    # Outline KB
    OUTLINE_API_URL: str = "https://outline.home.lan"
    OUTLINE_API_KEY: str = ""
    OUTLINE_COLLECTION: str = ""  # Collection ID for auto-generated articles
    
    # Application
    APP_NAME: str = "sapphire-support-core"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # FreeScout (optional)
    FREESCOUT_ENABLED: bool = False
    FREESCOUT_API_URL: str = ""
    FREESCOUT_API_KEY: str = ""
    
    # CRM (optional)
    CRM_WEBHOOK_URL: str = ""
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables (like NEXT_PUBLIC_* from portal)


settings = Settings()

