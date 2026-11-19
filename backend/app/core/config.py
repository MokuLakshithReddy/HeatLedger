import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development") # development | staging | production
    DEBUG: bool = Field(default=True)
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    
    # Security
    APP_SECRET_KEY: str = Field(default="dev-insecure-secret-key-change-in-production-min-32-chars")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8081",
            "http://10.0.2.2:8000",
        ]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        return ["*"]
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./heatledger.db")
    TEST_DATABASE_URL: str = Field(default="sqlite:///./test_heatledger.db")
    
    # Storage
    STORAGE_BACKEND: str = Field(default="local") # local | supabase | s3
    LOCAL_STORAGE_DIR: str = Field(default="./uploads/private")
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=10 * 1024 * 1024) # 10MB
    S3_BUCKET_NAME: Optional[str] = Field(default=None)
    S3_REGION_NAME: str = Field(default="ap-south-1")
    S3_ENDPOINT_URL: Optional[str] = Field(default=None)
    S3_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    S3_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    
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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()
