from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
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
    iss: Optional[str] = None
    aud: Optional[str] = None

class UserRegister(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=72)
    full_name: Optional[str] = None
    # Security SEC-01: Public registration only permits worker role.
    role: Optional[str] = Field(default="worker")
    preferred_language: str = Field(default="en") # en, te, hi
    # Optional worker details
    primary_platforms: Optional[List[str]] = Field(default_factory=list)
    vehicle_type: Optional[str] = None
    city: Optional[str] = "Hyderabad"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if v is not None and v != "worker":
            raise ValueError(
                "Privilege escalation prevented: Public self-registration is restricted to worker accounts. "
                "Privileged accounts (system_admin, organisation_admin) must be provisioned by an administrator."
            )
        return "worker"

class UserLogin(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str = Field(min_length=1, max_length=72)

class UserRoleUpdate(BaseModel):
    role: str = Field(description="Assigned role: worker, organisation_admin, organisation_viewer, system_admin")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ["worker", "organisation_admin", "organisation_viewer", "system_admin"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return v

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
