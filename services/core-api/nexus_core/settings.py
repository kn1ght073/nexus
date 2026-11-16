"""NEXUS Core configuration.

All values can be overridden by environment variables (NEXUS_*) or a .env
file next to the package, per the deployment layout in the architecture plan
(loopback for dev, LAN bind + firewall rule for deployment).
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service ---
    service_name: str = "nexus-core"
    host: str = "127.0.0.1"          # loopback for dev; set 0.0.0.0 for LAN deployment
    port: int = 8000

    # --- Database ---
    database_path: Path = Path("nexus.db")
    # Full SQLAlchemy URL (postgresql://...) — takes precedence over the path.
    # Used by the hosted control plane (Render + Neon/Supabase free tiers).
    database_url: str | None = None

    # --- Deployment mode ---
    # True on the hosted control plane: only auth/devices/activity/nodes
    # routers mount (no personal-data endpoints). See create_app().
    control_plane_mode: bool = False

    # A node counts as active while its heartbeat is younger than this.
    node_heartbeat_timeout: int = 90  # seconds

    # --- Security ---
    # Generated once at first boot and persisted so tokens survive restarts.
    # On ephemeral hosts (Render) set NEXUS_JWT_SECRET explicitly — a random
    # secret would otherwise be regenerated on every deploy and log everyone
    # out.
    jwt_secret: str | None = None
    jwt_secret_file: Path = Path("nexus_jwt_secret")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30

    # --- Files (path jail; the endpoint never escapes these roots) ---
    storage_roots: list[str] = [str(Path.home() / "Documents")]
    max_search_results: int = 50
    max_search_depth: int = 6

    # --- CORS (tauri://localhost + vite dev server; never "*") ---
    cors_origins: list[str] = ["tauri://localhost", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
