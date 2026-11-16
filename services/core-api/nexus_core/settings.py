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

    # --- Brute-force defense (hosted control plane + node) ---
    # login/register rate limit per (IP, email), and account lockout after
    # too many wrong passwords. Defaults leave humans unhindered while
    # making online guessing hopeless.
    auth_rate_limit: int = 10          # attempts per window per key
    auth_rate_window: int = 60         # seconds
    auth_lockout_attempts: int = 5     # wrong passwords before lockout
    auth_lockout_seconds: int = 300    # lockout cool-off (5 min)

    # --- Request hygiene on the public internet ---
    # /docs and /openapi.json are hidden unless NEXUS_EXPOSE_DOCS=true
    # (develop locally with it on). JSON body cap keeps one request from
    # eating memory on a 512 MB free instance (inbox audio is the ceiling).
    expose_docs: bool = False
    max_body_bytes: int = 10_000_000

    # --- Secure relay (node <-> control plane, no open ports on the node) ---
    # The node holds ONE outbound WebSocket to the control plane; devices
    # attach through authenticated, end-to-end-sealed frames. See
    # nexus_core/pairing.py and routers/relay.py.
    relay_enabled: bool = True
    pairing_code_ttl: int = 600        # seconds a pairing code stays valid
    pairing_max_attempts: int = 5     # wrong codes before the session dies

    # --- Node bridge (nexus_core/node_bridge.py) ---
    # Set by the CLI/desktop app when the user picks "this machine as main
    # server"; standalone runs may prefer the nexus_node.json file.
    node_bridge_cp_url: str | None = None
    node_bridge_id: int | None = None
    node_bridge_key: str | None = None

    # --- Files (path jail; the endpoint never escapes these roots) ---
    storage_roots: list[str] = [str(Path.home() / "Documents")]
    max_search_results: int = 50
    max_search_depth: int = 6

    # --- CORS (tauri://localhost + vite dev server; never "*") ---
    cors_origins: list[str] = ["tauri://localhost", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
