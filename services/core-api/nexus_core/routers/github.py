"""GitHub account linking (OAuth) + GitHub highlights, gh-CLI-style.

How popular GitHub-hosted apps connect with users (researched, cited in
docs/deploy/online-access.md):
- **gh CLI** (github.com/cli/cli) defaults to a *web-based browser flow*
  that is really the OAuth **device flow**: no localhost redirect; the CLI
  POSTs `client_id` (+scope) to `github.com/login/device/code`, shows a
  one-time user code + `github.com/login/device` URL, then polls
  `login/oauth/access_token` with
  `grant_type=urn:ietf:params:oauth:grant-type:device_code` until the user
  approves. The token lands in the system credential store
  (cli.github.com/manual/gh_auth_login).
- **Desktop/mobile apps** use the **authorize-code flow**
  (`github.com/login/oauth/authorize` → callback with `code`+`state` →
  token exchange). GitHub Apps are preferred over OAuth apps for
  fine-grained permissions; an OAuth app with the minimal `read:user`
  scope is the least-privilege choice for profile-only use
  (docs.github.com "Differences between GitHub Apps and OAuth apps").

How we view their GitHub highlights (the data surface):
- `GET /users/{username}` — login/avatar/name/bio/company/location/
  public_repos/public_gists/followers/following
  (docs.github.com/en/rest/users/users).
- `GET /users/{username}/repos?sort=updated` — repositories.
- `GET /users/{username}/events/public` — recent public activity feed.
- Unauthenticated REST is limited to **60 req/hour per IP (shared!)**;
  token-authenticated requests get **5,000/hour**
  (docs.github.com REST rate-limits doc). The node therefore proxies and
  caches: one linked token serves the user's apps, a 5-minute cache
  absorbs repeated dashboard views.

Endpoints here:
- POST /github/device/start      → user_code + verification URL + interval
- POST /github/device/poll       → token + linked profile (or pending/denied/slow_down)
- GET  /github/authorize-url     → URL the desktop app opens (state bound to the user)
- POST /github/authorize/callback→ code+state exchange → linked profile
- GET  /github/status           → linked? (login, scopes; never the token)
- DELETE /github/link            → unlink (+ best-effort server-side revocation)
- GET  /github/highlights        → profile + top repos + recent events (cached)
"""
from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone

import requests as _requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import log_activity
from ..models import GithubLink, User
from ..security import get_current_user
from ..settings import get_settings

router = APIRouter(prefix="/github", tags=["github"])
_settings = get_settings()

# --- minimal request/response schemas (kept local: github-only) ---
class DeviceStartRequest(BaseModel):
    """Optionally override the default minimal scope (read:user)."""
    scopes: str | None = None


class DeviceStartResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class DevicePollRequest(BaseModel):
    device_code: str


class GithubProfileOut(BaseModel):
    github_id: int
    login: str
    scopes: str
    linked_at: datetime


class DevicePollResponse(BaseModel):
    status: str                      # linked | pending | slow_down | expired | denied | error
    profile: GithubProfileOut | None = None
    detail: str | None = None


class AuthorizeURLRequest(BaseModel):
    scopes: str | None = None


class AuthorizeURLResponse(BaseModel):
    url: str
    state: str
    expires_in: int


class AuthorizeCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)
    state: str = Field(min_length=8, max_length=128)


class HighlightsOut(BaseModel):
    login: str
    github_id: int
    profile: dict
    repos: list[dict] = []
    events: list[dict] = []
    generated_at: datetime
    cached: bool = False
    rate_remaining: int | None = None


# --- in-memory OAuth session state (single-node; DB for anything durable) ---
_pending_device: dict[str, dict] = {}      # device_code -> {user_id, expires, interval}
_pending_authorize: dict[str, dict] = {}   # state -> {user_id, expires}
_highlights_cache: dict[int, dict] = {}    # user_id -> {payload, expires}


def _github_login(ep: str) -> str:
    return f"{_settings.github_login_base.rstrip('/')}/{ep.lstrip('/')}"


def _github_api(ep: str) -> str:
    return f"{_settings.github_api_base.rstrip('/')}/{ep.lstrip('/')}"


def _exchange_device_code(client_id: str, device_code: str) -> dict:
    """Poll GitHub's token endpoint (device grant). Returns parsed JSON."""
    r = _requests.post(
        _github_login("login/oauth/access_token"),
        json={
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_token_scopes(headers: dict) -> str:
    """GitHub returns granted scopes on the X-OAuth-Scopes response header."""
    raw = headers.get("X-OAuth-Scopes", "")
    return raw or "read:user"


def _fetch_github_profile(token: str) -> tuple[dict, str]:
    """GET /user with the linked token — id/login are trusted; the profile
    body feeds highlights. Returns (profile_json, granted_scopes)."""
    r = _requests.get(
        _github_api("user"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json(), _fetch_token_scopes(r.headers)


def _upsert_link(db: Session, user: User, token: str, scopes: str) -> GithubLink:
    profile, granted = _fetch_github_profile(token)
    link = db.query(GithubLink).filter(GithubLink.owner_id == user.id).first()
    if link is None:
        link = GithubLink(owner_id=user.id)
        db.add(link)
    link.github_id = int(profile["id"])
    link.github_login = str(profile["login"])
    link.access_token = token
    link.scopes = granted or scopes or ""
    db.commit()
    db.refresh(link)
    return link


def _link_out(link: GithubLink) -> GithubProfileOut:
    return GithubProfileOut(
        github_id=link.github_id,
        login=link.github_login,
        scopes=link.scopes,
        linked_at=link.linked_at,
    )


@router.post("/device/start", response_model=DeviceStartResponse)
def device_start(
    body: DeviceStartRequest | None = None,
    current_user: User = Depends(get_current_user),
):
    """Begin the gh-CLI-style device flow: returns the user code to enter at
    github.com/login/device plus the device_code this client will poll."""
    if not _settings.github_client_id:
        raise HTTPException(
            status_code=503,
            detail="GitHub linking is not configured on this node (missing client id).",
        )
    scopes = (body.scopes if body and body.scopes else None) or _settings.github_scopes
    r = _requests.post(
        _github_login("login/device/code"),
        json={"client_id": _settings.github_client_id, "scope": scopes},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"github device code request failed: {r.status_code}")
    data = r.json()
    _pending_device[data["device_code"]] = {
        "user_id": current_user.id,
        "expires": time.monotonic() + int(data.get("expires_in", 900)),
    }
    return DeviceStartResponse(
        device_code=data["device_code"],
        user_code=data["user_code"],
        verification_uri=data.get("verification_uri", "https://github.com/login/device"),
        expires_in=int(data.get("expires_in", 900)),
        interval=int(data.get("interval", 5)),
    )


@router.post("/device/poll", response_model=DevicePollResponse)
def device_poll(
    body: DevicePollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll for the linked token after the user entered the code at
    github.com/login/device. Translates GitHub's device-grant errors into
    stable statuses (pending / slow_down / expired / denied / error)."""
    pending = _pending_device.get(body.device_code)
    if pending is None:
        raise HTTPException(status_code=404, detail="Unknown device_code — call /device/start again.")
    if pending["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="This device code belongs to another session.")
    if time.monotonic() > pending["expires"]:
        _pending_device.pop(body.device_code, None)
        return DevicePollResponse(status="expired", detail="device code expired — start again")

    try:
        data = _exchange_device_code(_settings.github_client_id, body.device_code)
    except _requests.RequestException as exc:
        return DevicePollResponse(status="error", detail=f"github unreachable: {exc}")

    err = data.get("error")
    if err == "authorization_pending":
        return DevicePollResponse(status="pending", detail="user hasn't entered the code yet")
    if err == "slow_down":
        return DevicePollResponse(status="slow_down", detail="polling too fast — add 5s")
    if err in ("expired_token", "unsupported_grant_type"):
        _pending_device.pop(body.device_code, None)
        return DevicePollResponse(status="expired", detail=err)
    if err == "access_denied":
        _pending_device.pop(body.device_code, None)
        return DevicePollResponse(status="denied", detail="user denied at github.com/login/device")
    token = data.get("access_token")
    if not token:
        return DevicePollResponse(status="error", detail=f"unexpected response: {data}")

    _pending_device.pop(body.device_code, None)
    link = _upsert_link(db, current_user, token, _settings.github_scopes)
    log_activity(db, user_id=current_user.id, action="github.link", detail=f"login={link.github_login} flow=device")
    db.commit()
    return DevicePollResponse(status="linked", profile=_link_out(link))


@router.get("/authorize-url", response_model=AuthorizeURLResponse)
def authorize_url(
    body: AuthorizeURLRequest | None = None,
    current_user: User = Depends(get_current_user),
):
    """Build the github.com/login/oauth/authorize URL for the desktop app's
    'Connect GitHub' button. The returned state is bound to this user and
    single-use; the app opens the URL in a browser and then posts the
    code+state it received back to /authorize/callback."""
    if not _settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub linking is not configured (missing client id).")
    scopes = (body.scopes if body and body.scopes else None) or _settings.github_scopes
    state = secrets.token_urlsafe(32)
    _pending_authorize[state] = {
        "user_id": current_user.id,
        "expires": time.monotonic() + _settings.github_state_ttl,
    }
    params = {
        "client_id": _settings.github_client_id,
        "scope": scopes,
        "state": state,
    }
    if _settings.github_redirect_uri:
        params["redirect_uri"] = _settings.github_redirect_uri
    from urllib.parse import urlencode

    url = _github_login("login/oauth/authorize") + "?" + urlencode(params)
    return AuthorizeURLResponse(url=url, state=state, expires_in=_settings.github_state_ttl)


@router.post("/authorize/callback", response_model=DevicePollResponse)
def authorize_callback(
    body: AuthorizeCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange the authorize-code flow's code+state for a linked token."""
    pending = _pending_authorize.pop(body.state, None)
    if pending is None:
        raise HTTPException(status_code=400, detail="unknown or already-used state")
    if pending["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="state was issued to another session")
    if time.monotonic() > pending["expires"]:
        raise HTTPException(status_code=400, detail="state expired — request a fresh authorize url")
    if not _settings.github_client_id or not _settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub linking is not configured (missing secret)")
    r = _requests.post(
        _github_login("login/oauth/access_token"),
        json={
            "client_id": _settings.github_client_id,
            "client_secret": _settings.github_client_secret,
            "code": body.code,
            "redirect_uri": _settings.github_redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"github token exchange failed: {r.status_code}")
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail=f"github refused the code: {data.get('error', data)}")
    link = _upsert_link(db, current_user, token, _settings.github_scopes)
    log_activity(db, user_id=current_user.id, action="github.link", detail=f"login={link.github_login} flow=authorize")
    db.commit()
    return DevicePollResponse(status="linked", profile=_link_out(link))


@router.get("/status")
def github_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Is this account linked to GitHub? (Never exposes the token.)"""
    link = db.query(GithubLink).filter(GithubLink.owner_id == current_user.id).first()
    if link is None:
        return {"linked": False, "profile": None}
    return {"linked": True, "profile": _link_out(link).model_dump(mode="json")}


@router.delete("/link", status_code=204)
def unlink(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink GitHub and ask GitHub to revoke the token server-side
    (best-effort; works even if we never get a 200)."""
    link = db.query(GithubLink).filter(GithubLink.owner_id == current_user.id).first()
    if link is None:
        raise HTTPException(status_code=404, detail="no GitHub account linked")
    try:
        _requests.delete(
            f"{_github_api('applications')}/{_settings.github_client_id}/token",
            auth=(_settings.github_client_id or "", _settings.github_client_secret or ""),
            json={"access_token": link.access_token},
            timeout=15,
        )
    except _requests.RequestException:
        pass  # offline / not configured: local unlink still proceeds
    db.delete(link)
    db.commit()
    log_activity(db, user_id=current_user.id, action="github.unlink", detail=f"login={link.github_login}")
    db.commit()


@router.get("/highlights", response_model=HighlightsOut)
def highlights(
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GitHub highlights: profile + top repos + recent public events.

    Served from the node's cache (default 5 min) unless refresh=true —
    one linked token keeps every device's dashboard inside GitHub's
    5,000/hr authenticated limit instead of hammering 60/hr per-IP.
    """
    link = db.query(GithubLink).filter(GithubLink.owner_id == current_user.id).first()
    if link is None:
        raise HTTPException(
            status_code=409,
            detail="No GitHub account linked — start with POST /github/device/start or GET /github/authorize-url.",
        )
    cached = _highlights_cache.get(current_user.id)
    if cached and not refresh and time.monotonic() < cached["expires"]:
        payload = cached["payload"]
        payload["cached"] = True
        return HighlightsOut(**payload)

    headers = {
        "Authorization": f"Bearer {link.access_token}",
        "Accept": "application/vnd.github+json",
    }
    login = link.github_login
    try:
        profile_r = _requests.get(_github_api("user"), headers=headers, timeout=15)
        repos_r = _requests.get(
            _github_api(f"users/{login}/repos"),
            headers=headers,
            params={"sort": "updated", "per_page": 5},
            timeout=15,
        )
        events_r = _requests.get(
            _github_api(f"users/{login}/events/public"),
            headers=headers,
            params={"per_page": 5},
            timeout=15,
        )
    except _requests.RequestException as exc:
        if cached:
            payload = dict(cached["payload"], cached=True)
            payload["detail"] = f"stale cache served (github unreachable: {exc})"
            return HighlightsOut(**payload)
        raise HTTPException(status_code=502, detail=f"github unreachable: {exc}")

    if profile_r.status_code == 401:
        raise HTTPException(
            status_code=409,
            detail="GitHub token no longer valid — unlink and re-link (POST /github/device/start).",
        )
    profile_r.raise_for_status()

    repos = repos_r.json() if repos_r.status_code == 200 else []
    events = events_r.json() if events_r.status_code == 200 else []

    slim_repos = [
        {
            "name": r.get("name"),
            "stars": r.get("stargazers_count", 0),
            "language": r.get("language"),
            "description": (r.get("description") or "")[:120] or None,
            "html_url": r.get("html_url"),
            "pushed_at": r.get("pushed_at"),
        }
        for r in repos
    ]
    slim_events = [
        {
            "type": e.get("type"),
            "repo": (e.get("repo") or {}).get("name"),
            "created_at": e.get("created_at"),
            "detail": _event_detail(e),
        }
        for e in events
    ]
    p = profile_r.json()
    payload = {
        "login": p.get("login", login),
        "github_id": p.get("id", link.github_id),
        "profile": {
            "name": p.get("name"),
            "avatar_url": p.get("avatar_url"),
            "bio": p.get("bio"),
            "company": p.get("company"),
            "location": p.get("location"),
            "public_repos": p.get("public_repos"),
            "public_gists": p.get("public_gists"),
            "followers": p.get("followers"),
            "following": p.get("following"),
            "html_url": p.get("html_url"),
        },
        "repos": slim_repos,
        "events": slim_events,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
        "rate_remaining": int(profile_r.headers.get("x-ratelimit-remaining", 0)) or None,
    }
    _highlights_cache[current_user.id] = {
        "payload": payload,
        "expires": time.monotonic() + _settings.github_cache_seconds,
    }
    return HighlightsOut(**payload)


def _event_detail(e: dict) -> str:
    """One human-readable line per public event (PushEvent etc.)."""
    t = e.get("type")
    repo = (e.get("repo") or {}).get("name", "")
    if t == "PushEvent":
        n = len((e.get("payload") or {}).get("commits", []))
        return f"pushed {n} commit(s) to {repo}"
    if t in ("CreateEvent", "DeleteEvent"):
        return f"{t[:6].lower()} {(e.get('payload') or {}).get('ref_type', '?')} {repo}".strip()
    if t == "WatchEvent":
        return f"starred {repo}"
    if t == "ForkEvent":
        return f"forked {repo}"
    if t == "IssuesEvent":
        return f"{(e.get('payload') or {}).get('action', '?')} an issue on {repo}"
    if t == "PullRequestEvent":
        return f"{(e.get('payload') or {}).get('action', '?')} a PR on {repo}"
    return f"{t or 'event'} on {repo}"
