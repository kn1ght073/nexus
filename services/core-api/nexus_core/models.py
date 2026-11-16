"""SQLAlchemy models for the NEXUS Core data model.

Fixes vs. the previous flat models.py (per the Errors & Fixes file):
- Task and Note carry their own owner_id + created/updated/deleted columns,
  so every query can be ownership-filtered (was: GET /tasks and /notes
  returned every user's rows).
- UTC-aware timestamps (datetime.utcnow is deprecated).
- Capability flags on Device, per the architecture plan's device model.
"""
from datetime import datetime, timezone

import json

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    platform = Column(String, nullable=False)  # windows | macos | android | linux | cli
    capabilities = Column(String, default="")  # comma-separated: filesystem,notifications,...
    is_online = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    registered_at = Column(DateTime, default=utcnow, nullable=False)
    last_seen = Column(DateTime, default=utcnow, nullable=False)

    owner = relationship("User", back_populates="devices")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # tombstone for sync
    revision = Column(Integer, default=1, nullable=False, index=True)  # sync: bumped on every mutation

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending | in_progress | completed
    due_date = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    revision = Column(Integer, default=1, nullable=False, index=True)  # sync: bumped on every mutation

    project = relationship("Project", back_populates="tasks")
    owner = relationship("User", back_populates="tasks")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    revision = Column(Integer, default=1, nullable=False, index=True)  # sync: bumped on every mutation

    project = relationship("Project", back_populates="notes")
    owner = relationship("User", back_populates="notes")


class Activity(Base):
    """Append-only activity log: every mutating action leaves a trail (security §6)."""
    __tablename__ = "activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False, index=True)   # login, project.created, ...
    detail = Column(String, default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class InboxItem(Base):
    """Universal Inbox job: capture-anything, processed by the AI pipeline.

    kind: text | audio. For audio, `content` holds the stored blob path.
    Status machine: pending -> processing -> completed | rejected | failed.
    """
    __tablename__ = "inbox_items"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False)                 # text | audio
    content = Column(String, nullable=False)              # text body or audio path
    transcript = Column(String, nullable=True)            # STT output (audio)
    backend = Column(String, nullable=True)               # stt backend used
    result = Column(String, nullable=True)                # JSON result of the action engine
    error = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Node(Base):
    """A machine that can become the main NEXUS server (Mac/Windows node).

    The hosted control plane stores only this coordination record — never
    personal data. `is_active` marks the node currently serving the user;
    `last_seen` older than the heartbeat timeout means it went offline.
    services_json is configuration only: which optional services (stt, ...)
    are installed on the node.
    """
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                 # e.g. "Karthik's MacBook"
    platform = Column(String, nullable=False)             # macos | windows | linux
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    services_json = Column(String, default="{}")          # {"stt": "faster-whisper", ...}
    # How clients reach the node: LAN host[:port], Tailscale name/MagicDNS,
    # or a tunnel URL (cloudflared/ngrok). Plain config, not personal data.
    endpoint = Column(String, nullable=True)
    api_key = Column(String, nullable=True)               # token the node presents on claim
    registered_at = Column(DateTime, default=utcnow, nullable=False)
    last_seen = Column(DateTime, default=utcnow, nullable=False)

    owner = relationship("User", backref="nodes")

    @property
    def services(self) -> dict:
        try:
            return json.loads(self.services_json) if self.services_json else {}
        except ValueError:
            return {}


class PairingSession(Base):
    """A short-lived device-pairing handshake on the control plane.

    Flow (nexus_core/pairing.py): the owner (logged in on the phone/desktop
    app) asks the control plane for a pairing code; a new device proves
    knowledge of the code during the relay handshake and receives a scoped
    device token. Only the salted HMAC challenge is stored — the plaintext
    code exists nowhere but the owner's screen and the device's keypad for
    ten minutes.
    """
    __tablename__ = "pairing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)
    salt = Column(String, nullable=False)
    challenge = Column(String, nullable=False)            # HMAC(salt, code)
    device_name = Column(String, default="")
    attempts = Column(Integer, default=0, nullable=False) # wrong-code counter
    status = Column(String, default="pending", nullable=False)  # pending | completed | expired
    created_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    owner = relationship("User", backref="pairing_sessions")


class GithubLink(Base):
    """A user's linked GitHub account (see routers/github.py).

    Flow: the node (as an OAuth app) walks the user through GitHub's
    device or authorize-code flow and keeps ONE access token here so the
    node can render "GitHub highlights" with the 5000/hr authenticated
    rate limit instead of the 60/hr per-IP public one. Minimal scope
    ("read:user") is requested; the token is revocable at any time via
    unlink, which also asks GitHub to revoke it server-side.
    """
    __tablename__ = "github_links"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    github_id = Column(Integer, nullable=False, index=True)
    github_login = Column(String, nullable=False, index=True)
    access_token = Column(String, nullable=False)      # never returned by the API
    scopes = Column(String, default="", nullable=False)
    linked_at = Column(DateTime, default=utcnow, nullable=False)
    last_refreshed_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    owner = relationship("User", backref="github_link")


class RelayLink(Base):
    """Persistent device→node attachment served by the control plane.

    Written once when a paired device attaches to the node's relay socket,
    so the activity log can answer "which devices ever relayed through my
    account" — coordination metadata, not content. Relay frame bodies
    never touch the database.
    """
    __tablename__ = "relay_links"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    attached_at = Column(DateTime, default=utcnow, nullable=False)
    detached_at = Column(DateTime, nullable=True)
