"""Password hashing (Argon2id) and JWT access/refresh tokens.

Replaces the mock auth (mock-token-123 / auto-created users) that the Errors
& Fixes file flagged as security errors C2/D2. The JWT secret is generated at
first boot and persisted next to the database; tokens carry the user id,
device id and scope so the dependency chain can enforce least privilege.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .settings import get_settings

_settings = get_settings()
_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)


def _load_or_create_secret() -> str:
    """Load the persisted JWT secret or generate one at first boot."""
    path = _settings.jwt_secret_file
    if path.exists():
        stored = path.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    token = secrets.token_hex(32)
    path.write_text(token, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows ignores POSIX modes; best effort
    return token


JWT_SECRET = _load_or_create_secret()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False  # malformed hash etc.


def create_token(
    user_id: int,
    token_type: Literal["access", "refresh"] = "access",
    device_id: int | None = None,
    scope: str = "user",
) -> str:
    if token_type == "access":
        expiry = datetime.now(timezone.utc) + timedelta(minutes=_settings.access_token_minutes)
    else:
        expiry = datetime.now(timezone.utc) + timedelta(days=_settings.refresh_token_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "scope": scope,
        "exp": expiry,
        "iat": datetime.now(timezone.utc),
    }
    if device_id is not None:
        payload["dev"] = device_id
    return jwt.encode(payload, JWT_SECRET, algorithm=_settings.jwt_algorithm)


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[_settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise credentials_error
    if payload.get("type") != expected_type:
        raise credentials_error
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: Bearer access token -> active User row."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
