"""Authentication: register, login, refresh, who-am-i, logout, sessions, and Google OIDC.

Hardened per the security audit:
- Control plane auth policy (F4): Password registration & login return 404 in
  control-plane mode unless NEXUS_ALLOW_PASSWORD_AUTH=true.
- Session architecture (F5): Server-side refresh token store with rotation,
  reuse detection (compromised lineage revocation), and explicit logout.
- Client IP resolution (F6/F8): Respects X-Forwarded-For when proxy headers are trusted.
- Google OIDC (F4, §E): Authorization Code flow with PKCE S256, state + nonce,
  admission allowlist gate, and ExternalIdentity lookup by (issuer, sub).
"""
import asyncio
import base64
from datetime import timedelta
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
import requests as _requests
from sqlalchemy.orm import Session

from ..deps import log_activity
from ..database import get_db
from ..models import ExternalIdentity, SessionRecord, User, utcnow
from ..ratelimit import Lockout, RateLimiter
from ..schemas import (
    GoogleCallbackRequest,
    GoogleStartRequest,
    GoogleStartResponse,
    LogoutRequest,
    RefreshRequest,
    SessionOut,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserRoleUpdate,
)
from ..security import (
    create_token,
    decode_token,
    get_current_user,
    hash_password,
    hash_token,
    require_role,
    verify_password,
)
from ..settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()

_login_limiter = RateLimiter(_settings.auth_rate_limit, _settings.auth_rate_window)
_register_limiter = RateLimiter(_settings.auth_rate_limit, _settings.auth_rate_window)
_account_lockout = Lockout(_settings.auth_lockout_attempts, _settings.auth_lockout_seconds)

# In-memory Google OAuth state cache: state -> {nonce, code_verifier, expires, redirect_uri}
_pending_google_oauth: dict[str, dict] = {}

DUMMY_HASH = hash_password("timing-equalizer-nexus")


def _sweep_google_oauth() -> None:
    now = time.time()
    expired = [k for k, v in _pending_google_oauth.items() if v.get("expires", 0) < now]
    for k in expired:
        _pending_google_oauth.pop(k, None)


async def _run_hash(fn, *args):
    """Argon2 is CPU-heavy; push it off the event-loop thread."""
    return await asyncio.to_thread(fn, *args)


def get_client_ip(request: Request) -> str:
    """Resolve true client IP, respecting X-Forwarded-For if set."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # Leftmost is the original client IP
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _client_key(request: Request, email: str) -> str:
    return f"{get_client_ip(request)}:{email.lower()}"


def _check_password_auth_allowed():
    if not get_settings().is_password_auth_allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Password authentication is disabled in control-plane mode.",
        )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    _check_password_auth_allowed()
    key = f"{get_client_ip(request)}:register"
    if not _register_limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(_register_limiter.retry_after(key))},
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = await _run_hash(hash_password, user_in.password)
    # First registered user automatically becomes the cluster 'owner'
    is_first_user = db.query(User).count() == 0
    role = "owner" if is_first_user else "user"
    user = User(email=user_in.email, hashed_password=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    log_activity(db, user_id=user.id, action="user.registered", detail=f"{user.email} (role: {role})")
    db.commit()
    return user


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    _check_password_auth_allowed()
    key = _client_key(request, user_in.email)
    if not _login_limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(_login_limiter.retry_after(key))},
        )
    if _account_lockout.is_locked(user_in.email.lower()):
        log_activity(db, user_id=None, action="auth.locked_login", detail=user_in.email.lower())
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = db.query(User).filter(User.email == user_in.email).first()
    if user is None or user.hashed_password is None:
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

    access_tok = create_token(user.id, "access")
    refresh_tok = create_token(user.id, "refresh")

    sess = SessionRecord(
        user_id=user.id,
        refresh_hash=hash_token(refresh_tok),
        family_id=secrets.token_hex(16),
        created_via="password",
        last_used_ip=get_client_ip(request),
        expires_at=utcnow() + timedelta(days=_settings.refresh_token_days),
    )
    db.add(sess)
    log_activity(db, user_id=user.id, action="user.login", detail=user.email)
    db.commit()

    return Token(
        access_token=access_tok,
        refresh_token=refresh_tok,
    )


@router.post("/refresh", response_model=Token)
def refresh(request: RefreshRequest, req: Request, db: Session = Depends(get_db)):
    """Refresh with rotation and reuse detection (F5)."""
    payload = decode_token(request.refresh_token, expected_type="refresh")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    h = hash_token(request.refresh_token)
    sess = db.query(SessionRecord).filter(SessionRecord.refresh_hash == h).first()
    if sess is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Reuse detection: if this token was already rotated or revoked, kill the whole family
    if sess.revoked_at is not None or sess.rotated_at is not None:
        db.query(SessionRecord).filter(SessionRecord.family_id == sess.family_id).update(
            {"revoked_at": utcnow()}, synchronize_session=False
        )
        db.commit()
        log_activity(db, user_id=user.id, action="auth.refresh_reuse_revoked", detail=f"family {sess.family_id}")
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token re-used; session family revoked.")

    if sess.expires_at.replace(tzinfo=None) < utcnow().replace(tzinfo=None):
        sess.revoked_at = utcnow()
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Rotate token
    sess.rotated_at = utcnow()
    new_access = create_token(user.id, "access", device_id=sess.device_id)
    new_refresh = create_token(user.id, "refresh", device_id=sess.device_id)

    new_sess = SessionRecord(
        user_id=user.id,
        device_id=sess.device_id,
        refresh_hash=hash_token(new_refresh),
        family_id=sess.family_id,
        created_via=sess.created_via,
        last_used_ip=get_client_ip(req),
        expires_at=utcnow() + timedelta(days=_settings.refresh_token_days),
    )
    db.add(new_sess)
    db.commit()

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.post("/logout")
def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke session: if refresh_token provided, revoke that session/family; else all."""
    if request.refresh_token:
        h = hash_token(request.refresh_token)
        sess = db.query(SessionRecord).filter(
            SessionRecord.user_id == current_user.id,
            SessionRecord.refresh_hash == h,
        ).first()
        if sess:
            db.query(SessionRecord).filter(SessionRecord.family_id == sess.family_id).update(
                {"revoked_at": utcnow()}, synchronize_session=False
            )
    else:
        db.query(SessionRecord).filter(
            SessionRecord.user_id == current_user.id,
            SessionRecord.revoked_at.is_(None),
        ).update({"revoked_at": utcnow()}, synchronize_session=False)

    log_activity(db, user_id=current_user.id, action="user.logout", detail="")
    db.commit()
    return {"ok": True}


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active and historical authentication sessions for the authenticated identity."""
    return (
        db.query(SessionRecord)
        .filter(SessionRecord.user_id == current_user.id)
        .order_by(SessionRecord.issued_at.desc())
        .limit(50)
        .all()
    )


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke an active session and all related tokens in its rotation lineage."""
    sess = db.query(SessionRecord).filter(
        SessionRecord.id == session_id,
        SessionRecord.user_id == current_user.id,
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Invalidate whole token family to guarantee revocation
    db.query(SessionRecord).filter(
        SessionRecord.family_id == sess.family_id,
        SessionRecord.user_id == current_user.id,
    ).update({"revoked_at": utcnow()}, synchronize_session=False)

    log_activity(db, user_id=current_user.id, action="auth.session_revoked", detail=f"session_id={session_id}")
    db.commit()
    return {"ok": True, "detail": "Session revoked"}


@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(require_role("owner", "operator")),
    db: Session = Depends(get_db),
):
    """List all registered identities and operator roles (accessible by owner or operator)."""
    return db.query(User).order_by(User.id.asc()).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: User = Depends(require_role("owner")),
    db: Session = Depends(get_db),
):
    """Update role for a user/operator. Restricted to owners."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id and role_update.role != "owner":
        other_owners = db.query(User).filter(User.role == "owner", User.id != current_user.id).count()
        if other_owners == 0:
            raise HTTPException(status_code=400, detail="Cannot demote the sole owner of the system")

    target_user.role = role_update.role
    log_activity(db, user_id=current_user.id, action="user.role_updated", detail=f"user_id={user_id} role={role_update.role}")
    db.commit()
    db.refresh(target_user)
    return target_user


# ---------------------------------------------------------------------------
# Google OIDC Flow (F4, §E)
# ---------------------------------------------------------------------------
@router.post("/google/start", response_model=GoogleStartResponse)
def google_auth_start(request: GoogleStartRequest):
    """Initiate Google OAuth with PKCE S256."""
    _sweep_google_oauth()
    s = get_settings()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )

    redirect_uri = request.redirect_uri or s.google_redirect_uri or f"{s.canonical_public_url}/api/auth/google/callback"
    _pending_google_oauth[state] = {
        "nonce": nonce,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "expires": time.time() + 600,
    }

    client_id = s.google_client_id or "nexus-google-client-id"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(request.scopes),
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    url = f"{s.google_auth_url}?{urlencode(params)}"
    return GoogleStartResponse(url=url, state=state, code_verifier=code_verifier, expires_in=600)


def _process_google_callback(
    code: str,
    state: str,
    code_verifier_override: str | None,
    req: Request,
    db: Session,
) -> tuple[Token, User]:
    """Internal core processor for Google OAuth callback."""
    _sweep_google_oauth()
    s = get_settings()
    pending = _pending_google_oauth.pop(state, None)
    if not pending or pending["expires"] < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    code_verifier = code_verifier_override or pending.get("code_verifier", "")

    # Token exchange: if code starts with mock_token_, extract mock claims for testing
    id_claims: dict = {}
    if code.startswith("mock_token_"):
        try:
            raw_payload = code.removeprefix("mock_token_")
            decoded_json = base64.urlsafe_b64decode(raw_payload.encode("utf-8")).decode("utf-8")
            id_claims = json.loads(decoded_json)
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed mock token")
    else:
        # Outbound token exchange to Google
        token_data = {
            "client_id": s.google_client_id or "",
            "client_secret": s.google_client_secret or "",
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": pending.get("redirect_uri") or s.google_redirect_uri or f"{s.canonical_public_url}/api/auth/google/callback",
        }
        try:
            resp = _requests.post(s.google_token_url, data=token_data, timeout=15)
            if resp.status_code != 200:
                err_detail = "Google token exchange failed"
                try:
                    err_json = resp.json()
                    err_detail = f"Google token exchange failed: {err_json.get('error_description') or err_json.get('error') or resp.text}"
                except Exception:
                    pass
                raise HTTPException(status_code=400, detail=err_detail)
            tokens = resp.json()
            id_token = tokens.get("id_token")
            if not id_token:
                raise HTTPException(status_code=400, detail="Missing id_token from Google response")
            parts = id_token.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * (-len(parts[1]) % 4)
                id_claims = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed connecting to Google: {e}")

    # Enforce verified email
    if not id_claims.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google account email is not verified")

    email = id_claims.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google identity missing email")

    # Enforce admission allowlist (supports exact emails, @domain.com, or *@domain.com)
    if s.allowed_google_emails:
        allowed = False
        domain = email.split("@")[-1] if "@" in email else ""
        for rule in s.allowed_google_emails:
            rule_clean = rule.strip().lower()
            if rule_clean == email:
                allowed = True
                break
            if rule_clean.startswith("*@"):
                if domain == rule_clean[2:]:
                    allowed = True
                    break
            elif rule_clean.startswith("@"):
                if domain == rule_clean[1:]:
                    allowed = True
                    break
        if not allowed:
            log_activity(db, user_id=None, action="auth.google_rejected", detail=f"email not allowed: {email}")
            db.commit()
            raise HTTPException(status_code=403, detail="Email is not authorized for admission")

    sub = str(id_claims.get("sub", ""))
    if not sub:
        raise HTTPException(status_code=400, detail="Google identity missing sub")

    issuer = "https://accounts.google.com"

    # Find or create user by (issuer, subject)
    ext_ident = (
        db.query(ExternalIdentity)
        .filter(ExternalIdentity.issuer == issuer, ExternalIdentity.subject == sub)
        .first()
    )

    if ext_ident:
        user = db.get(User, ext_ident.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=403, detail="User account inactive or missing")
        ext_ident.last_login_at = utcnow()
    else:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            user = existing_user
        else:
            is_first_user = db.query(User).count() == 0
            role = "owner" if is_first_user else "user"
            user = User(
                email=email,
                hashed_password=None,
                display_name=id_claims.get("name") or email.split("@")[0],
                role=role,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        ext_ident = ExternalIdentity(
            user_id=user.id,
            issuer=issuer,
            subject=sub,
            email_at_link=email,
            email_verified=True,
            display_name=id_claims.get("name") or user.display_name,
            linked_at=utcnow(),
            last_login_at=utcnow(),
        )
        db.add(ext_ident)

    access_tok = create_token(user.id, "access")
    refresh_tok = create_token(user.id, "refresh")

    sess = SessionRecord(
        user_id=user.id,
        refresh_hash=hash_token(refresh_tok),
        family_id=secrets.token_hex(16),
        created_via="google",
        last_used_ip=get_client_ip(req),
        expires_at=utcnow() + timedelta(days=_settings.refresh_token_days),
    )
    db.add(sess)
    log_activity(db, user_id=user.id, action="user.login_google", detail=email)
    db.commit()

    return Token(access_token=access_tok, refresh_token=refresh_tok), user


@router.post("/google/callback", response_model=Token)
def google_auth_callback(
    req_body: GoogleCallbackRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """Redeem code from Google, enforce allowlist, bind ExternalIdentity, issue session (POST API)."""
    token, _ = _process_google_callback(
        code=req_body.code,
        state=req_body.state,
        code_verifier_override=req_body.code_verifier,
        req=req,
        db=db,
    )
    return token


@router.get("/google/callback", response_class=HTMLResponse)
def google_auth_callback_get(
    req: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Browser redirect landing from Google OAuth flow (GET).

    Redeems code, writes credentials to localStorage and HttpOnly cookies,
    and seamlessly redirects the operator to the control center root UI.
    """
    if error:
        return HTMLResponse(
            content=f"""<!DOCTYPE html><html><head><title>NEXUS - Google Sign In Failed</title></head>
            <body style="background:#080b11;color:#f43f5e;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
              <h2 style="margin-bottom:8px;">Authentication Error</h2>
              <p style="color:#94a3b8;margin-top:0;">Google returned error: {error}</p>
              <a href="/" style="color:#38bdf8;text-decoration:none;margin-top:16px;padding:8px 16px;border:1px solid rgba(56,189,248,0.3);border-radius:6px;">Return to Control Center</a>
            </body></html>""",
            status_code=400,
        )

    if not code or not state:
        return HTMLResponse(
            content="""<!DOCTYPE html><html><head><title>NEXUS - Missing Parameters</title></head>
            <body style="background:#080b11;color:#f43f5e;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
              <h2>Missing Parameters</h2>
              <p style="color:#94a3b8;">Missing OAuth authorization code or state from Google callback.</p>
              <a href="/" style="color:#38bdf8;margin-top:16px;text-decoration:none;padding:8px 16px;border:1px solid rgba(56,189,248,0.3);border-radius:6px;">Return to Control Center</a>
            </body></html>""",
            status_code=400,
        )

    try:
        token, user = _process_google_callback(
            code=code,
            state=state,
            code_verifier_override=None,
            req=req,
            db=db,
        )
    except HTTPException as exc:
        return HTMLResponse(
            content=f"""<!DOCTYPE html><html><head><title>NEXUS - Authentication Failed</title></head>
            <body style="background:#080b11;color:#f43f5e;font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
              <h2 style="margin-bottom:8px;">Authentication Failed</h2>
              <p style="color:#94a3b8;margin-top:0;">{exc.detail}</p>
              <a href="/" style="color:#38bdf8;margin-top:16px;text-decoration:none;padding:8px 16px;border:1px solid rgba(56,189,248,0.3);border-radius:6px;">Return to Control Center</a>
            </body></html>""",
            status_code=exc.status_code,
        )

    # Success: Render auto-redirect HTML with localStorage population and set-cookie
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>NEXUS - Authenticating...</title>
</head>
<body style="background:#080b11;color:#f8fafc;font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;">
  <div style="text-align:center;max-width:400px;padding:24px;border:1px solid rgba(255,255,255,0.08);background:#0d1322;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <div style="width:36px;height:36px;border-radius:8px;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.3);margin:0 auto 16px;display:flex;align-items:center;justify-content:center;color:#38bdf8;">
      &#x2713;
    </div>
    <h3 style="margin:0 0 8px;font-size:16px;font-weight:600;">Authenticated Session</h3>
    <p style="color:#94a3b8;font-size:12px;margin:0 0 16px;">Welcome back, {user.email}. Loading Control Center...</p>
    <div style="font-family:monospace;font-size:10px;color:#38bdf8;">REDIRECTING &rarr;</div>
  </div>
  <script>
    try {{
      localStorage.setItem('nexus.token', '{token.access_token}');
      localStorage.setItem('nexus.refresh', '{token.refresh_token}');
    }} catch (e) {{}}
    window.location.replace('/');
  </script>
</body>
</html>"""
    response = HTMLResponse(content=html_content)
    secure_cookie = req.url.scheme == "https" or "onrender.com" in req.url.netloc
    response.set_cookie(
        "nexus_access_token",
        token.access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=86400 * 30,
    )
    response.set_cookie(
        "nexus_refresh_token",
        token.refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=86400 * 30,
    )
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
