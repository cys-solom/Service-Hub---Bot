"""Security — JWT auth, password hashing, RBAC"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings

security_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password using bcrypt via direct module, with fallback to SHA-256"""
    try:
        import bcrypt
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
    except Exception:
        # Fallback: SHA-256 with salt
        salt = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:16]
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        # Fallback: SHA-256
        salt = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:16]
        return hashlib.sha256(f"{salt}{plain}".encode()).hexdigest() == hashed


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    """FastAPI dependency -- validates JWT and returns admin payload"""
    payload = decode_token(credentials.credentials)
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return payload


def check_permission(required: str):
    """Decorator-style dependency for RBAC"""
    async def _check(admin=Depends(get_current_admin)):
        permissions = admin.get("permissions", [])
        is_super = admin.get("is_super", False)
        if not is_super and required not in permissions:
            raise HTTPException(status_code=403, detail=f"Permission '{required}' required")
        return admin
    return _check
