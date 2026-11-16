"""Authentication: register, login, refresh, who-am-i.

Replaces mock auth (login auto-created users and returned
mock_token_for_{id}; get_current_user returned the first user in the DB).

Hardening (public-internet posture): login and register are rate-limited
per (client IP, email) and accounts lock for a cool-off period after a few
wrong passwords — online guessing is hopeless without rendering the account
permanently unusable. Lock/limit responses look exactly like ordinary 401s
to an attacker (the account-exists question is never answerable), while
the Retry-After header tells the honest client when to come back.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..deps import log_activity
from ..database import get_db
from ..models import User
from ..ratelimit import Lockout, RateLimiter
from ..schemas import RefreshRequest, Token, UserCreate, UserLogin, UserOut
from ..security import (
    create_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()

_login_limiter = RateLimiter(_settings.auth_rate_limit, _settings.auth_rate_window)
_register_limiter = RateLimiter(_settings.auth_rate_limit, _settings.auth_rate_window)
_account_lockout = Lockout(_settings.auth_lockout_attempts, _settings.auth_lockout_seconds)

# A real Argon2 hash of a throwaway password: compared when the email is
# unknown so response timing cannot reveal whether an account exists.
DUMMY_HASH = hash_password("timing-equalizer-nexus")


async def _run_hash(fn, *args):
    """Argon2 is CPU-heavy; push it off the event-loop thread."""
    return await asyncio.to_thread(fn, *args)


def _client_key(request: Request, email: str) -> str:
    client_ip = (request.client.host if request.client else "unknown") + ":" + email.lower()
    return client_ip


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    key = (request.client.host if request.client else "unknown") + ":register"
    if not _register_limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(_register_limiter.retry_after(key))},
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = await _run_hash(hash_password, user_in.password)
    user = User(email=user_in.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    log_activity(db, user_id=user.id, action="user.registered", detail=user.email)
    db.commit()
    return user


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    key = _client_key(request, user_in.email)
    if not _login_limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(_login_limiter.retry_after(key))},
        )
    # Locked accounts answer exactly like unknown ones: same 401 body, no
    # Retry-After — an observer cannot distinguish lockout from a bad email.
    if _account_lockout.is_locked(user_in.email.lower()):
        log_activity(db, user_id=-1, action="auth.locked_login", detail=user_in.email.lower())
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = db.query(User).filter(User.email == user_in.email).first()
    if user is None:
        # still burn a hash comparison so timing cannot reveal account existence
        await _run_hash(verify_password, DUMMY_HASH, user_in.password)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    ok = await _run_hash(verify_password, user.hashed_password, user_in.password)
    if not ok:
        _account_lockout.record_failure(user_in.email.lower())
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")
    _account_lockout.record_success(user_in.email.lower())
    _login_limiter.reset(key)
    log_activity(db, user_id=user.id, action="user.login", detail=user.email)
    db.commit()
    return Token(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.post("/refresh", response_model=Token)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token, expected_type="refresh")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return Token(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
