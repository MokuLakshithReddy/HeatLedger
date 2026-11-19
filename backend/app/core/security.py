from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status
from backend.app.core.config import settings

ALLOWED_ALGORITHMS = ["HS256", "RS256", "ES256"]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode("utf-8")
        if len(pw_bytes) > 72:
            return False
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes (Bcrypt algorithm limit).")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "heatledger-auth",
        "aud": "heatledger-api",
    })
    algorithm = settings.ALGORITHM
    if algorithm not in ALLOWED_ALGORITHMS:
        algorithm = "HS256"
    encoded_jwt = jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=algorithm)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    algorithm = settings.ALGORITHM if settings.ALGORITHM in ALLOWED_ALGORITHMS else "HS256"
    try:
        payload = jwt.decode(
            token,
            settings.APP_SECRET_KEY,
            algorithms=[algorithm],
            issuer="heatledger-auth",
            audience="heatledger-api",
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
