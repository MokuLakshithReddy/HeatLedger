import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    
    # Security
    APP_SECRET_KEY: str = Field(default="dev-insecure-secret-key-change-in-production-min-32-chars")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./heatledger.db")
    TEST_DATABASE_URL: str = Field(default="sqlite:///./test_heatledger.db")
    
    # Storage
    STORAGE_BACKEND: str = Field(default="local") # local | supabase | s3
    LOCAL_STORAGE_DIR: str = Field(default="./uploads/private")
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=10 * 1024 * 1024) # 10MB
    
    # AI / LLM
    LLM_PROVIDER: str = Field(default="mock") # mock | gemini | openai
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    LLM_MODEL_NAME: str = Field(default="gemini-1.5-flash")
    
    # Weather Providers
    IMD_API_KEY: Optional[str] = Field(default=None)
    IMD_BASE_URL: str = Field(default="https://api.imd.gov.in/public/api/")
    CDS_API_KEY: Optional[str] = Field(default=None)
    CDS_API_URL: str = Field(default="https://cds.climate.copernicus.eu/api/v2")
    
    # Demographics & Geography defaults (Hyderabad, India)
    DEMO_MODE: bool = Field(default=True)
    DEFAULT_TIMEZONE: str = Field(default="Asia/Kolkata")
    HYDERABAD_LATITUDE: float = Field(default=17.3850)
    HYDERABAD_LONGITUDE: float = Field(default=78.4867)
    
    # Privacy / Cohort safeguards
    MINIMUM_COHORT_SIZE: int = Field(default=5) # k-anonymity minimum cohort size

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
