export interface HealthCheckResponse {
  status: string;
  service: string;
  mode: string;
}

export interface UserOut {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  is_locked: boolean;
  display_name?: string | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface GoogleIdentityOut {
  id: number;
  email: string;
  name: string;
  picture?: string | null;
  verified_email: boolean;
}

export interface AccountOverviewResponse {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  google_identity: GoogleIdentityOut | null;
  device_count: number;
  primary_node: string | null;
  metrics: {
    projects: number;
    tasks: number;
    notes: number;
    files: number;
  };
}

export interface DeviceOut {
  id: number;
  name: string;
  platform: string;
  capabilities: string;
  is_online: boolean;
  last_seen: string;
  created_at: string;
}

export interface NodeOut {
  id: number;
  name: string;
  platform: string;
  endpoint: string | null;
  is_active: boolean;
  is_online?: boolean;
  last_seen: string | null;
}

export interface ActiveNodeResponse {
  active_node: NodeOut | null;
  endpoint: string | null;
  online: boolean;
}

export interface TaskOut {
  id: number;
  title: string;
  description?: string | null;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority?: number;
  project_id?: number | null;
  due_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectOut {
  id: number;
  title: string;
  description?: string | null;
  status?: string;
  created_at: string;
  updated_at: string;
}

export interface NoteOut {
  id: number;
  title: string;
  content: string;
  tags?: string;
  project_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified_at: string;
}

export interface StorageRootsResponse {
  roots: string[];
}

export interface SyncChanges {
  projects: ProjectOut[];
  tasks: TaskOut[];
  notes: NoteOut[];
}

export interface SyncPullResponse {
  server_time: string;
  changes: SyncChanges;
}

export interface ActivityEvent {
  id: number;
  action: string;
  detail?: string | null;
  device_id?: number | null;
  created_at: string;
}
