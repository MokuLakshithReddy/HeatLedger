from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, get_password_hash, create_access_token
from backend.app.core.config import settings
from backend.app.models.entities import User, WorkerProfile, Organisation, OrganisationMember, utc_now
from backend.app.schemas.auth import UserRegister, UserLogin, Token, UserResponse, UserPreferencesUpdate
from backend.app.api.deps import get_current_user, log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])

def lookup_auth_user(db: Session, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[User]:
    bind = db.get_bind()
    if bind and bind.dialect.name == "postgresql":
        from sqlalchemy import text
        row = db.execute(
            text("SELECT id, email, phone, hashed_password, role, is_active, preferred_language, full_name FROM authenticate_user_lookup(:email, :phone)"),
            {"email": email, "phone": phone}
        ).first()
        if row:
            return User(
                id=row.id,
                email=row.email,
                phone=row.phone,
                hashed_password=row.hashed_password,
                role=row.role,
                is_active=row.is_active,
                preferred_language=row.preferred_language,
                full_name=row.full_name,
            )
        return None
    else:
        if email:
            return db.query(User).filter(User.email == email).first()
        if phone:
            return db.query(User).filter(User.phone == phone).first()
        return None

@router.post("/register", response_model=Token)
def register_user(
    reg_in: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    # SEC-01: Public registration strictly creates worker role
    assigned_role = "worker"
    
    # Check if email or phone already exists
    if reg_in.email and lookup_auth_user(db, email=reg_in.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if reg_in.phone and lookup_auth_user(db, phone=reg_in.phone):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")
    
    from backend.app.models.entities import generate_uuid
    user_id = generate_uuid()

    # SEC-RLS: Set session identity BEFORE inserting user or refreshing post-commit
    db.info["current_user_id"] = str(user_id)
    db.info["current_user_role"] = str(assigned_role)
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            from sqlalchemy import text
            db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user_id)})
            db.execute(text("SELECT set_config('app.current_user_role', :role, false)"), {"role": str(assigned_role)})
    except Exception:
        pass

    hashed_pw = get_password_hash(reg_in.password)
    user = User(
        id=user_id,
        email=reg_in.email,
        phone=reg_in.phone,
        hashed_password=hashed_pw,
        full_name=reg_in.full_name,
        role=assigned_role,
        preferred_language=reg_in.preferred_language,
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(user)

    # Worker profile
    profile = WorkerProfile(
        user_id=user_id,
        primary_platforms=reg_in.primary_platforms or [],
        vehicle_type=reg_in.vehicle_type,
        city=reg_in.city or "Hyderabad",
        consented_location_tracking=False, # Disabled by default until explicit consent
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    log_audit(db, user.id, "USER_REGISTERED", "User", user.id, {"role": user.role}, request)

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role, "email": user.email}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user_id=user.id,
        role=user.role,
        preferred_language=user.preferred_language,
    )

@router.post("/login", response_model=Token)
def login_user(
    login_in: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    user = lookup_auth_user(db, email=login_in.email, phone=login_in.phone)

    # SEC-05: Uniform error to prevent account enumeration
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    log_audit(db, user.id, "USER_LOGGED_IN", "User", user.id, None, request)

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role, "email": user.email}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user_id=user.id,
        role=user.role,
        preferred_language=user.preferred_language,
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
