"""Pydantic request/response schemas.

Kept compatible with the existing CLI payloads (title/description/status/
project_id) so apps/cli keeps working unchanged, while adding the fields the
architecture plan requires: ids, timestamps, capabilities and sync metadata.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

TaskStatus = Literal["pending", "in_progress", "completed"]


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str = "user"
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: Literal["user", "operator", "owner"]


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class SessionOut(BaseModel):
    id: int
    device_id: int | None = None
    created_via: str
    last_used_ip: str | None = None
    issued_at: datetime
    expires_at: datetime
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GoogleStartRequest(BaseModel):
    redirect_uri: str | None = None
    scopes: list[str] = ["openid", "email", "profile"]


class GoogleStartResponse(BaseModel):
    url: str
    state: str
    code_verifier: str
    expires_in: int = 600


class GoogleCallbackRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=8)
    code_verifier: str | None = None


# --- Devices ---
class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    platform: Literal["windows", "macos", "android", "linux", "cli"]
    capabilities: list[str] = Field(default_factory=list)  # filesystem, notifications, ...


class DeviceOut(BaseModel):
    id: int
    name: str
    platform: str
    capabilities: list[str]
    is_online: bool
    registered_at: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _split_capabilities(cls, data):
        # ORM stores capabilities as "filesystem,notifications"; expose as list
        if hasattr(data, "capabilities") and isinstance(data.capabilities, str):
            return {
                "id": data.id,
                "name": data.name,
                "platform": data.platform,
                "capabilities": [c for c in data.capabilities.split(",") if c],
                "is_online": data.is_online,
                "registered_at": data.registered_at,
                "last_seen": data.last_seen,
            }
        return data



# --- Device tokens (step 2: per-device scopes) ---
class DeviceTokenRequest(BaseModel):
    scopes: list[str] = Field(default_factory=list)  # subset of device capabilities (+ read)


class DeviceTokenResponse(BaseModel):
    access_token: str
    scope: str
    device_id: int


# --- Projects ---
class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = "pending"


class ProjectOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    revision: int

    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: TaskStatus


# --- Tasks ---
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = "pending"
    project_id: int | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    due_date: datetime | None
    project_id: int | None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    revision: int

    model_config = ConfigDict(from_attributes=True)


# --- Notes ---
class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    project_id: int | None = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    project_id: int | None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    revision: int

    model_config = ConfigDict(from_attributes=True)


# --- Activity ---
class ActivityOut(BaseModel):
    id: int
    action: str
    detail: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# --- Sync push (step 2) ---
class PushItem(BaseModel):
    """One client-side change. id must be None for creates."""
    id: int | None = None
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    content: str | None = None
    project_id: int | None = None
    revision: int = Field(ge=1, description="client's last-known revision of this row")
    deleted: bool = False


class SyncPushRequest(BaseModel):
    tasks: list[PushItem] = []
    notes: list[PushItem] = []
    projects: list[PushItem] = []


class PushResult(BaseModel):
    id: int | None
    accepted: bool
    server_revision: int
    conflict: bool = False
    reason: str | None = None


class SyncPushResponse(BaseModel):
    results: dict[str, list[PushResult]]


# --- Files ---
class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int


class SearchResult(BaseModel):
    path: str
    match_context: str


# --- Sync (foundation for the plan's /sync/pull + /sync/push) ---
class SyncPullRequest(BaseModel):
    since: datetime | None = None


class ChangedItems(BaseModel):
    projects: list[ProjectOut] = []
    tasks: list[TaskOut] = []
    notes: list[NoteOut] = []


class SyncPullResponse(BaseModel):
    server_time: datetime
    changes: ChangedItems


# --- Nodes (control plane coordination; config only, no personal data) ---
class NodeClaimRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)          # e.g. "Karthik's MacBook"
    platform: str = Field(pattern="^(macos|windows|linux)$")
    endpoint: str | None = Field(default=None, max_length=300)  # host:port / tailscale name / tunnel URL


class NodeServicesRequest(BaseModel):
    services: dict[str, str] = Field(default_factory=dict)   # {"stt": "faster-whisper", ...}


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str
    is_active: bool
    is_online: bool = False                                   # computed from heartbeat age
    services: dict[str, str] = {}
    endpoint: str | None = None
    registered_at: datetime
    last_seen: datetime


class NodeOutWithSecret(NodeOut):
    """Claim response: includes the node api_key exactly once, at claim time."""
    api_key: str


# --- Pairing (device <-> node via the control plane; see pairing.py) ---
class PairingCodeRequest(BaseModel):
    """Owner asks for a fresh pairing code (shows it on their screen)."""
    device_name: str = Field(default="", max_length=100)


class PairingCodeResponse(BaseModel):
    """The code itself + where to enter it. Plaintext appears exactly once."""
    pairing_id: int
    code: str
    expires_at: datetime
    relay_url: str  # wss://<control-plane>/relay/attach — where the device connects


class PairingCompleteRequest(BaseModel):
    """Device side of the handshake: prove code knowledge + name yourself."""
    pairing_id: int
    code: str = Field(pattern="^[0-9]{6}$")
    device_name: str = Field(default="", max_length=100)
    platform: str = Field(default="android", pattern="^(android|ios|windows|macos|linux|web|cli)$")


class PairingCompleteResponse(BaseModel):
    """What a successfully paired device receives: a scoped token + node info."""
    device_id: int
    token: str  # scoped device token (scopes: capture, read, sync)
    node: NodeOut | None  # where to relay through (null until the node dials in)


# --- Node services (installable STT/LLM; node-side only) ---
class ServiceStatusResponse(BaseModel):
    installed: dict[str, str] = {}          # {"stt": "faster-whisper"}
    available: dict[str, str] = {}          # human-readable descriptions


class ServiceInstallRequest(BaseModel):
    service: str = Field(pattern="^(stt|llm|bootstrap)$")
    model: str | None = None               # base|small (stt) | llama3.2|qwen2.5:3b (llm) | mirror name (bootstrap)


class ServiceInstallStatus(BaseModel):
    id: int
    service: str
    model: str
    status: str                            # running | completed | failed
    steps: list[str] = []
    error: str | None = None
