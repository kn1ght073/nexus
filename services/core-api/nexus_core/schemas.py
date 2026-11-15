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
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


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

    model_config = ConfigDict(from_attributes=True)


# --- Activity ---
class ActivityOut(BaseModel):
    id: int
    action: str
    detail: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
