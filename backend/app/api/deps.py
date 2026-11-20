from typing import Optional, Generator, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
import hashlib
from decimal import Decimal

def sanitize_metadata(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: sanitize_metadata(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_metadata(v) for v in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif hasattr(data, "isoformat"):
        return data.isoformat()
    return data

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.core.logging import logger
from backend.app.models.entities import User, OrganisationMember, AuditLog, utc_now

security = HTTPBearer(auto_error=False)

def hash_ip(ip_address: Optional[str]) -> Optional[str]:
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Propagate session identity to PostgreSQL for Row Level Security (RLS)
    db.info["current_user_id"] = str(user.id)
    db.info["current_user_role"] = str(user.role)
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user.id)})
            db.execute(text("SELECT set_config('app.current_user_role', :role, true)"), {"role": str(user.role)})
    except Exception as e:
        logger.warning(f"Could not set PostgreSQL RLS session variables: {e}")

    return user

def get_current_worker(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "worker" and current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to worker accounts",
        )
    return current_user

def get_current_org_member(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role not in ("organisation_admin", "organisation_viewer", "system_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to approved organisation personnel",
        )
    return current_user

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to system administrators",
        )
    return current_user

def log_audit(
    db: Session,
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    metadata_json: Optional[dict] = None,
    request: Optional[Request] = None,
):
    ip_hash = None
    if request and request.client:
        ip_hash = hash_ip(request.client.host)
    
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=sanitize_metadata(metadata_json) if metadata_json else None,
        ip_hash=ip_hash,
        timestamp=utc_now(),
    )
    db.add(audit_entry)
    db.commit()
