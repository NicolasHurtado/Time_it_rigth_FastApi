"""Security utilities for JWT tokens and password hashing"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)  # type: ignore


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    return encoded_jwt  # type: ignore


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload  # type: ignore
    except JWTError:
        return None


def create_token_for_user(user_id: int, username: str) -> str:
    """Create access token for a specific user"""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

    token_data = {"sub": str(user_id), "username": username, "type": "access"}

    return create_access_token(data=token_data, expires_delta=access_token_expires)
