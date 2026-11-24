"""NEXUS Core configuration.

All values can be overridden by environment variables (NEXUS_*) or a .env
file next to the package, per the deployment layout in the architecture plan
(loopback for dev, LAN bind + firewall rule for deployment).
"""
from functools import lru_cache
import json
from pathlib import Path

from pydantic import field_validator
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

    @property
    def resolved_database_path(self) -> Path:
        """Resolve persistent SQLite database path.
        Priority:
        1. Explicit path if database_path is set to non-default
        2. Local nexus.db in current working directory if it exists
        3. ~/.nexus/nexus.db persistent home directory
        """
        p = self.database_path
        if p and p != Path("nexus.db"):
            return p.expanduser().resolve()
        if Path("nexus.db").exists():
            return Path("nexus.db").resolve()
        default_dir = Path.home() / ".nexus"
        default_dir.mkdir(parents=True, exist_ok=True)
        return (default_dir / "nexus.db").resolve()

    # --- Deployment mode ---
    # True on the hosted control plane: only auth/devices/activity/nodes
    # routers mount (no personal-data endpoints). See create_app().
    control_plane_mode: bool = False
    allow_ephemeral_db: bool = False  # Set true to explicitly allow SQLite in control_plane_mode (dev/tests)

    # --- Single Unified Public Endpoint (Master Variable) ---
    # When deployed on Render or a custom domain, set NEXUS_PUBLIC_URL once
    # (e.g. https://nexus-control-plane-uvi8.onrender.com). All submodules,
    # OAuth redirects, web endpoints, and relay bridges derive from this single variable.
    public_url: str = "https://nexus-control-plane-uvi8.onrender.com"

    @property
    def canonical_public_url(self) -> str:
        url = (self.public_url or "").strip()
        if not url:
            return "http://127.0.0.1:8000"
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return url.rstrip("/")

    # --- Auth Admission Policy (F4, §E) ---
    # Disabled by default: Google OAuth is the SOLE supported authentication & registration method.
    allow_password_auth: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    allowed_google_emails: list[str] | str = []
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def is_password_auth_allowed(self) -> bool:
        return self.allow_password_auth

    @field_validator("allowed_google_emails", mode="before")
    @classmethod
    def _parse_allowed_emails(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        if isinstance(v, list):
            return [str(e).strip().lower() for e in v if str(e).strip()]
        return v or []

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

    # --- GitHub linking (routers/github.py) ---
    # The node acts as an OAuth "app" and links the user's GitHub account
    # (gh-CLI-style device flow for the CLI, authorize-code flow for the
    # desktop app). Defaults point at real GitHub; tests and the demo
    # harness point them at a local stub. Scopes stay MINIMAL — read-only
    # profile access is all "highlights" needs (least privilege, same
    # principle as the GitHub Apps guidance in the GitHub docs).
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_scopes: str = "read:user"
    github_login_base: str = "https://github.com"      # device/code + token endpoints
    github_api_base: str = "https://api.github.com"    # user/repos/events endpoints
    github_redirect_uri: str | None = None             # authorize-code callback (app default if unset)
    github_state_ttl: int = 600                        # seconds an OAuth `state` stays valid
    github_cache_seconds: int = 300                    # highlights cache (rate-limit QoL)

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

    @property
    def effective_cors_origins(self) -> list[str]:
        origins = list(self.cors_origins)
        pub = self.canonical_public_url
        if pub and pub not in origins:
            origins.append(pub)
        if not self.control_plane_mode:
            for o in [
                "http://localhost:8081",
                "http://127.0.0.1:8081",
                "http://localhost:19006",
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]:
                if o not in origins:
                    origins.append(o)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
