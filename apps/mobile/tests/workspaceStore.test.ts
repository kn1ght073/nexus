import {
  getLocalProjects,
  saveLocalProject,
  deleteLocalProject,
  getLocalTasks,
  saveLocalTask,
  updateLocalTask,
  deleteLocalTask,
  getLocalNotes,
  saveLocalNote,
  deleteLocalNote,
} from '../src/api/workspaceStore';

describe('NEXUS Mobile Workspace Local Store', () => {
  it('manages local projects with persistence and fallback', async () => {
    const initial = await getLocalProjects();
    expect(Array.isArray(initial)).toBe(true);
    expect(initial.length).toBeGreaterThanOrEqual(1);

    const created = await saveLocalProject({
      title: 'Autonomous Sentinel',
      description: 'Host anomaly detector',
      status: 'active',
    });
    expect(created.id).toBeDefined();
    expect(created.title).toBe('Autonomous Sentinel');

    const updated = await getLocalProjects();
    expect(updated[0].title).toBe('Autonomous Sentinel');

    await deleteLocalProject(created.id);
    const afterDelete = await getLocalProjects();
    expect(afterDelete.find((p) => p.id === created.id)).toBeUndefined();
  });

  it('manages local tasks with status transitions', async () => {
    const tasks = await getLocalTasks();
    expect(Array.isArray(tasks)).toBe(true);

    const task = await saveLocalTask({
      title: 'Deploy edge node daemon',
      status: 'pending',
    });
    expect(task.status).toBe('pending');

    const toggled = await updateLocalTask(task.id, { status: 'completed' });
    expect(toggled?.status).toBe('completed');

    await deleteLocalTask(task.id);
    const remaining = await getLocalTasks();
    expect(remaining.find((t) => t.id === task.id)).toBeUndefined();
  });

  it('manages local notes with tags', async () => {
    const notes = await getLocalNotes();
    expect(Array.isArray(notes)).toBe(true);

    const note = await saveLocalNote({
      title: 'Kernel callback table offsets',
      content: 'NtQuerySystemInformation system handle table parsing',
      tags: 're, kernel',
    });
    expect(note.title).toBe('Kernel callback table offsets');

    await deleteLocalNote(note.id);
    const remaining = await getLocalNotes();
    expect(remaining.find((n) => n.id === note.id)).toBeUndefined();
  });
});
