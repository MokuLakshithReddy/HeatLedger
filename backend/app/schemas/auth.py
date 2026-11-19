from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from backend.app.schemas.common import BaseSchema

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: str
    role: str
    preferred_language: str

class TokenPayload(BaseModel):
    sub: str
    role: str
    email: Optional[str] = None
    exp: Optional[int] = None

class UserRegister(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: str = Field(default="worker") # worker, organisation_admin, organisation_viewer
    preferred_language: str = Field(default="en") # en, te, hi
    # Optional worker details
    primary_platforms: Optional[List[str]] = Field(default_factory=list)
    vehicle_type: Optional[str] = None
    city: Optional[str] = "Hyderabad"

class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class UserResponse(BaseSchema):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    preferred_language: str
    is_active: bool
    created_at: datetime

class UserPreferencesUpdate(BaseModel):
    preferred_language: Optional[str] = None # en, te, hi
    full_name: Optional[str] = None
