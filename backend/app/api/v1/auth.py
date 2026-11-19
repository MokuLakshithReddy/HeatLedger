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

@router.post("/register", response_model=Token)
def register_user(
    reg_in: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    # SEC-01: Public registration strictly creates worker role
    assigned_role = "worker"
    
    # Check if email or phone already exists
    if reg_in.email:
        existing = db.query(User).filter(User.email == reg_in.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if reg_in.phone:
        existing = db.query(User).filter(User.phone == reg_in.phone).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already registered")
    
    hashed_pw = get_password_hash(reg_in.password)
    user = User(
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
    db.commit()
    db.refresh(user)

    # Worker profile
    profile = WorkerProfile(
        user_id=user.id,
        primary_platforms=reg_in.primary_platforms or [],
        vehicle_type=reg_in.vehicle_type,
        city=reg_in.city or "Hyderabad",
        consented_location_tracking=False, # Disabled by default until explicit consent
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(profile)
    db.commit()

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
    user = None
    if login_in.email:
        user = db.query(User).filter(User.email == login_in.email).first()
    elif login_in.phone:
        user = db.query(User).filter(User.phone == login_in.phone).first()

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
