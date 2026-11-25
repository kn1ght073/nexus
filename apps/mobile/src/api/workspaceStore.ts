/**
 * Workspace Local Store & Sync Buffer
 * 
 * Provides resilient offline/local-first persistence for Tasks, Projects, and Notes
 * on mobile. When connected to a full edge node, data syncs directly with the node.
 * When connected only to the cloud control plane (which intentionally stores zero
 * personal data to maintain user sovereignty), items are safely stored locally on
 * the device with an indicator that they will sync once an edge node connects.
 */

import { getSecureItem, setSecureItem } from '../utils/secureStore';
import { ProjectOut, TaskOut, NoteOut } from './types';

const LOCAL_PROJECTS_KEY = 'nexus_local_projects';
const LOCAL_TASKS_KEY = 'nexus_local_tasks';
const LOCAL_NOTES_KEY = 'nexus_local_notes';

// Default initial items for first-time onboarding
const INITIAL_PROJECTS: ProjectOut[] = [
  {
    id: 1001,
    title: 'Core Infrastructure',
    description: 'Personal server clustering, backup schedules, and edge node configuration.',
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 1002,
    title: 'Sovereign Workspace',
    description: 'Private documentation, local AI models, and secure vault storage.',
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const INITIAL_TASKS: TaskOut[] = [
  {
    id: 2001,
    title: 'Pair primary MacBook / desktop node',
    description: 'Run `nexus node claim` on your main workstation to link sovereign storage.',
    status: 'pending',
    priority: 1,
    project_id: 1001,
    due_date: new Date(Date.now() + 86400000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2002,
    title: 'Review storage root permissions',
    description: 'Ensure jailed storage roots in ~/.nexus/storage are configured.',
    status: 'completed',
    priority: 2,
    project_id: 1002,
    due_date: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const INITIAL_NOTES: NoteOut[] = [
  {
    id: 3001,
    title: 'Welcome to NEXUS Sovereign Hub',
    content: 'Your notes and tasks are strictly end-to-end sovereign. When an edge node is online, they replicate to your private disk.',
    tags: 'welcome, sovereign, security',
    project_id: 1001,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const INITIAL_PROJECT_IDS = new Set(INITIAL_PROJECTS.map((p) => p.id));
const INITIAL_TASK_IDS = new Set(INITIAL_TASKS.map((t) => t.id));
const INITIAL_NOTE_IDS = new Set(INITIAL_NOTES.map((n) => n.id));

export async function clearLocalWorkspace(): Promise<void> {
  await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify([]));
  await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify([]));
  await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify([]));
}

// --- Projects ---

export async function getLocalProjects(): Promise<ProjectOut[]> {
  const raw = await getSecureItem(LOCAL_PROJECTS_KEY);
  if (!raw) {
    await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify(INITIAL_PROJECTS));
    return INITIAL_PROJECTS;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return INITIAL_PROJECTS;
    const hasReal = parsed.some((p) => !INITIAL_PROJECT_IDS.has(p.id));
    return hasReal ? parsed.filter((p) => !INITIAL_PROJECT_IDS.has(p.id)) : parsed;
  } catch {
    return INITIAL_PROJECTS;
  }
}

export async function cacheRemoteProjects(projects: ProjectOut[]): Promise<void> {
  if (Array.isArray(projects)) {
    await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify(projects));
  }
}

export async function saveLocalProject(project: Omit<ProjectOut, 'id' | 'created_at' | 'updated_at'>): Promise<ProjectOut> {
  const current = await getLocalProjects();
  const realCurrent = current.filter((p) => !INITIAL_PROJECT_IDS.has(p.id));
  const newProj: ProjectOut = {
    id: Date.now(),
    title: project.title,
    description: project.description || null,
    status: project.status || 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  const updated = [newProj, ...realCurrent];
  await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify(updated));
  return newProj;
}

export async function deleteLocalProject(id: number): Promise<void> {
  const current = await getLocalProjects();
  const updated = current.filter((p) => p.id !== id);
  await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify(updated));
}

export async function updateLocalProject(id: number, patch: Partial<ProjectOut>): Promise<ProjectOut | null> {
  const current = await getLocalProjects();
  let updatedProj: ProjectOut | null = null;
  const updated = current.map((p) => {
    if (p.id === id) {
      updatedProj = { ...p, ...patch, updated_at: new Date().toISOString() };
      return updatedProj;
    }
    return p;
  });
  await setSecureItem(LOCAL_PROJECTS_KEY, JSON.stringify(updated));
  return updatedProj;
}

// --- Tasks ---

export async function getLocalTasks(): Promise<TaskOut[]> {
  const raw = await getSecureItem(LOCAL_TASKS_KEY);
  if (!raw) {
    await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify(INITIAL_TASKS));
    return INITIAL_TASKS;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return INITIAL_TASKS;
    const hasReal = parsed.some((t) => !INITIAL_TASK_IDS.has(t.id));
    return hasReal ? parsed.filter((t) => !INITIAL_TASK_IDS.has(t.id)) : parsed;
  } catch {
    return INITIAL_TASKS;
  }
}

export async function cacheRemoteTasks(tasks: TaskOut[]): Promise<void> {
  if (Array.isArray(tasks)) {
    await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify(tasks));
  }
}

export async function saveLocalTask(task: { title: string; description?: string; status?: 'pending' | 'in_progress' | 'completed' | 'cancelled'; priority?: number; project_id?: number | null; due_date?: string | null }): Promise<TaskOut> {
  const current = await getLocalTasks();
  const realCurrent = current.filter((t) => !INITIAL_TASK_IDS.has(t.id));
  const newTask: TaskOut = {
    id: Date.now(),
    title: task.title,
    description: task.description || null,
    status: task.status || 'pending',
    priority: task.priority || 1,
    project_id: task.project_id || null,
    due_date: task.due_date || null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  const updated = [newTask, ...realCurrent];
  await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify(updated));
  return newTask;
}

export async function updateLocalTask(id: number, patch: Partial<TaskOut>): Promise<TaskOut | null> {
  const current = await getLocalTasks();
  let updatedTask: TaskOut | null = null;
  const updated = current.map((t) => {
    if (t.id === id) {
      updatedTask = { ...t, ...patch, updated_at: new Date().toISOString() };
      return updatedTask;
    }
    return t;
  });
  await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify(updated));
  return updatedTask;
}

export async function deleteLocalTask(id: number): Promise<void> {
  const current = await getLocalTasks();
  const updated = current.filter((t) => t.id !== id);
  await setSecureItem(LOCAL_TASKS_KEY, JSON.stringify(updated));
}

// --- Notes ---

export async function getLocalNotes(): Promise<NoteOut[]> {
  const raw = await getSecureItem(LOCAL_NOTES_KEY);
  if (!raw) {
    await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify(INITIAL_NOTES));
    return INITIAL_NOTES;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return INITIAL_NOTES;
    const hasReal = parsed.some((n) => !INITIAL_NOTE_IDS.has(n.id));
    return hasReal ? parsed.filter((n) => !INITIAL_NOTE_IDS.has(n.id)) : parsed;
  } catch {
    return INITIAL_NOTES;
  }
}

export async function cacheRemoteNotes(notes: NoteOut[]): Promise<void> {
  if (Array.isArray(notes)) {
    await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify(notes));
  }
}

export async function saveLocalNote(note: { title: string; content: string; tags?: string; project_id?: number | null }): Promise<NoteOut> {
  const current = await getLocalNotes();
  const realCurrent = current.filter((n) => !INITIAL_NOTE_IDS.has(n.id));
  const newNote: NoteOut = {
    id: Date.now(),
    title: note.title,
    content: note.content,
    tags: note.tags || undefined,
    project_id: note.project_id || null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  const updated = [newNote, ...realCurrent];
  await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify(updated));
  return newNote;
}

export async function deleteLocalNote(id: number): Promise<void> {
  const current = await getLocalNotes();
  const updated = current.filter((n) => n.id !== id);
  await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify(updated));
}

export async function updateLocalNote(id: number, patch: Partial<NoteOut>): Promise<NoteOut | null> {
  const current = await getLocalNotes();
  let updatedNote: NoteOut | null = null;
  const updated = current.map((n) => {
    if (n.id === id) {
      updatedNote = { ...n, ...patch, updated_at: new Date().toISOString() };
      return updatedNote;
    }
    return n;
  });
  await setSecureItem(LOCAL_NOTES_KEY, JSON.stringify(updated));
  return updatedNote;
}
