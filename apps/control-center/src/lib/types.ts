export interface User {
  id: number;
  email: string;
  role: "user" | "operator" | "owner";
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface SessionRecord {
  id: number;
  device_id: number | null;
  created_via: string;
  last_used_ip: string | null;
  user_agent?: string | null;
  issued_at: string;
  expires_at: string;
  rotated_at: string | null;
  revoked_at: string | null;
}

export interface NodeRecord {
  id: number;
  name: string;
  platform: string;
  role?: string;
  lan_ip?: string;
  endpoint?: string;
  is_online?: boolean;
  last_seen: string | null;
  capabilities?: string;
}

export interface DeviceRecord {
  id: number;
  name: string;
  platform: "windows" | "macos" | "android" | "linux" | "cli";
  capabilities: string[];
  is_online: boolean;
  registered_at: string;
  last_seen: string;
}

export interface ActivityRecord {
  id: number;
  user_id?: number | null;
  device_id?: number | null;
  action: string;
  detail: string;
  created_at: string;
}

export interface SystemStatus {
  service: string;
  mode: string;
  database: {
    status: "connected" | "degraded" | "unavailable";
    latency_ms: number;
    engine: string;
    error?: string | null;
  };
  auth: {
    password_auth_allowed: boolean;
    google_oidc_configured: boolean;
    google_allowlist_active: boolean;
  };
  node_coordination: {
    heartbeat_timeout_sec: number;
    relay_enabled: boolean;
    pairing_ttl_sec: number;
  };
  operator: {
    user_id: number;
    email: string;
    role: "user" | "operator" | "owner";
  };
}

export interface RelayLinkRecord {
  id: number;
  node_id: number;
  device_id: number | null;
  attached_at: string | null;
  detached_at: string | null;
  is_active: boolean;
}

export interface RelayStatus {
  active_sockets: number;
  nodes_listening: Array<{
    node_id: number;
    has_device: boolean;
    owner_id: number;
  }>;
  recent_links: RelayLinkRecord[];
}

export interface ServicePackage {
  label: string;
  module: string;
  size_first_use: string;
  docs: string;
  install: string;
  prompt: string;
}

export interface PackagesResponse {
  services: Record<string, ServicePackage>;
  environment: {
    uv_available: boolean;
    venv_dir: string;
    python: string;
    index_url: string;
    requirements: string[];
    commands: string[];
    notes: string[];
  };
  mirrors: Record<string, string>;
  docs: Record<string, string>;
}

export interface ServiceStatusResponse {
  installed: Record<string, string>;
  available: Record<string, string>;
}

// --- Client Console Specific Types ---
export interface GoogleIdentity {
  linked: boolean;
  email: string | null;
  name: string | null;
  picture_url: string | null;
  email_verified: boolean;
  linked_at: string | null;
  last_login_at: string | null;
}

export interface AccountOverview {
  id: number;
  email: string;
  display_name: string | null;
  role: "user" | "operator" | "owner";
  is_active: boolean;
  created_at: string;
  google_identity: GoogleIdentity;
  device_stats: {
    total: number;
    active: number;
  };
  session_stats: {
    total: number;
    active: number;
  };
}

export interface ActivityPage {
  items: ActivityRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClientServerStatus {
  control_plane: string;
  api_version: string;
  mode: string;
  database: string;
  relay_mesh: string;
  auth_provider: string;
  checked_at: string;
  features: Record<string, boolean>;
}

export interface AccountDataSummary {
  profile: {
    id: number;
    email: string;
    display_name: string;
    role: string;
    created_at: string;
  };
  stats: {
    devices: number;
    projects: number;
    notes: number;
    tasks: number;
    inbox_items: number;
  };
  storage: {
    cloud_storage_policy: string;
    cloud_bytes_stored: number;
    local_node_storage: string;
    file_transfer_protocol: string;
  };
  capabilities: Record<string, string>;
}
