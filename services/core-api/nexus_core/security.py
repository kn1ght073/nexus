"""Password hashing (Argon2id) and JWT access/refresh tokens.

Replaces the mock auth (mock-token-123 / auto-created users) that the Errors
& Fixes file flagged as security errors C2/D2. The JWT secret is generated at
first boot and persisted next to the database; tokens carry the user id,
device id and scope so the dependency chain can enforce least privilege.
"""
import hashlib
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
    """Resolve the JWT secret.

    Precedence: NEXUS_JWT_SECRET env var (hosted control plane — a pinned
    secret survives Render's ephemeral filesystem; a random one would log
    everyone out on every deploy), then the persisted file (local node),
    then generate + persist.
    """
    if _settings.jwt_secret:
        return _settings.jwt_secret

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


def hash_token(token: str) -> str:
    """SHA256 hex digest of token for server-side session registry."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(
    user_id: int,
    token_type: Literal["access", "refresh"] = "access",
    device_id: int | None = None,
    scope: str = "user",
    jti: str | None = None,
) -> str:
    if token_type == "access":
        expiry = datetime.now(timezone.utc) + timedelta(minutes=_settings.access_token_minutes)
    else:
        expiry = datetime.now(timezone.utc) + timedelta(days=_settings.refresh_token_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "scope": scope,
        "jti": jti or secrets.token_hex(16),
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
    # attach token claims so scoped dependencies can reason about them
    setattr(user, "_token_scope", payload.get("scope", "user"))
    setattr(user, "_token_device_id", payload.get("dev"))
    return user


def require_scope(*allowed: str):
    """Dependency factory: require the token's scope to intersect `allowed`.

    Plain user tokens carry scope="user" (full access). Device tokens carry a
    comma-separated capability list (e.g. "read,filesystem"); they are only
    accepted if one of their capabilities is in `allowed`.
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        scope = getattr(current_user, "_token_scope", "user")
        if scope == "user":
            return current_user  # full-trust interactive token
        granted = {s for s in scope.split(",") if s}
        if not granted.intersection(allowed):
            raise HTTPException(
                status_code=403,
                detail=f"token scope '{scope}' lacks required scope {sorted(allowed)}",
            )
        return current_user

    return checker
