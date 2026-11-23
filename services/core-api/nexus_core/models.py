"""SQLAlchemy models for the NEXUS Core data model.

Hardened per the security audit:
- Explicit lengths on all String columns for strict Postgres VARCHAR DDL compatibility.
- User.hashed_password is nullable for Google-only OIDC accounts.
- UNIQUE constraint on github_links.github_id.
- ExternalIdentity for Google OIDC (RFC 9700 compliant, sub/issuer indexed).
- SessionRecord for server-side refresh token registry, rotation, and reuse detection.
"""
from datetime import datetime, timezone
import json

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # nullable for Google OIDC accounts
    display_name = Column(String(255), nullable=True)
    role = Column(String(32), default="user", nullable=False)  # 'user' | 'operator' | 'owner'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    external_identities = relationship("ExternalIdentity", back_populates="user", cascade="all, delete-orphan")
    auth_sessions = relationship("SessionRecord", back_populates="user", cascade="all, delete-orphan")


class ExternalIdentity(Base):
    """External OIDC/OAuth provider identities (Google). Keyed by (issuer, subject)."""
    __tablename__ = "external_identities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    issuer = Column(String(255), nullable=False)        # e.g. 'https://accounts.google.com'
    subject = Column(String(255), nullable=False)       # Google sub claim
    email_at_link = Column(String(255), nullable=True, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    display_name = Column(String(255), nullable=True)
    picture_url = Column(String(1024), nullable=True)
    linked_at = Column(DateTime, default=utcnow, nullable=False)
    last_login_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="external_identities")

    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_external_identities_issuer_subject"),
        UniqueConstraint("user_id", "issuer", name="uq_external_identities_user_issuer"),
    )


class SessionRecord(Base):
    """Server-side refresh-token registry supporting rotation and reuse detection."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    refresh_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA256 of token
    family_id = Column(String(64), index=True, nullable=False)                  # rotation lineage
    created_via = Column(String(32), default="password", nullable=False)        # 'password' | 'google'
    last_used_ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    issued_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    rotated_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="auth_sessions")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), index=True, nullable=False)
    platform = Column(String(32), nullable=False)  # windows | macos | android | linux | cli
    capabilities = Column(String(255), default="")  # comma-separated: filesystem,notifications,...
    is_online = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    registered_at = Column(DateTime, default=utcnow, nullable=False)
    last_seen = Column(DateTime, default=utcnow, nullable=False)

    owner = relationship("User", back_populates="devices")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(String(1024), nullable=True)
    status = Column(String(32), default="pending", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # tombstone for sync
    revision = Column(Integer, default=1, nullable=False, index=True)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(String(1024), nullable=True)
    status = Column(String(32), default="pending", nullable=False)  # pending | in_progress | completed
    due_date = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    revision = Column(Integer, default=1, nullable=False, index=True)

    project = relationship("Project", back_populates="tasks")
    owner = relationship("User", back_populates="tasks")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    content = Column(String(4096), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    revision = Column(Integer, default=1, nullable=False, index=True)

    project = relationship("Project", back_populates="notes")
    owner = relationship("User", back_populates="notes")


class Activity(Base):
    __tablename__ = "activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    detail = Column(String(512), default="")
    created_at = Column(DateTime, default=utcnow, nullable=False)


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(32), nullable=False)                 # text | audio
    content = Column(String(2048), nullable=False)             # text body or audio path
    transcript = Column(String(4096), nullable=True)           # STT output (audio)
    backend = Column(String(64), nullable=True)               # stt backend used
    result = Column(String(4096), nullable=True)              # JSON result of action engine
    error = Column(String(1024), nullable=True)
    status = Column(String(32), default="pending", nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    platform = Column(String(32), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    services_json = Column(String(1024), default="{}")
    endpoint = Column(String(255), nullable=True)
    api_key = Column(String(128), nullable=True)
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
    __tablename__ = "pairing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)
    salt = Column(String(64), nullable=False)
    challenge = Column(String(128), nullable=False)
    device_name = Column(String(128), default="")
    attempts = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    owner = relationship("User", backref="pairing_sessions")


class GithubLink(Base):
    __tablename__ = "github_links"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    github_id = Column(Integer, nullable=False, unique=True, index=True)  # UNIQUE per F30
    github_login = Column(String(128), nullable=False, index=True)
    access_token = Column(String(255), nullable=False)
    scopes = Column(String(255), default="", nullable=False)
    linked_at = Column(DateTime, default=utcnow, nullable=False)
    last_refreshed_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    owner = relationship("User", backref="github_link")


class RelayLink(Base):
    __tablename__ = "relay_links"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    attached_at = Column(DateTime, default=utcnow, nullable=False)
    detached_at = Column(DateTime, nullable=True)
