import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  Modal,
  ScrollView,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Plus,
  FolderGit2,
  Trash2,
  CheckCircle,
  Circle,
  X,
  FileText,
  CheckSquare,
  Search,
} from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { ProjectOut, TaskOut, NoteOut } from '../../../src/api/types';
import {
  getLocalProjects,
  saveLocalProject,
  updateLocalProject,
  deleteLocalProject,
  cacheRemoteProjects,
  getLocalTasks,
  saveLocalTask,
  updateLocalTask,
  deleteLocalTask,
  getLocalNotes,
  saveLocalNote,
  deleteLocalNote,
} from '../../../src/api/workspaceStore';

export default function ProjectsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');
  const [search, setSearch] = useState('');

  // Selected project for drilldown modal
  const [selectedProject, setSelectedProject] = useState<ProjectOut | null>(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [showAddNoteForm, setShowAddNoteForm] = useState(false);

  // Load projects
  const { data: projects, isLoading, refetch } = useQuery<ProjectOut[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      try {
        const remote = await apiClient<ProjectOut[]>('/api/projects');
        await cacheRemoteProjects(remote);
        return remote;
      } catch {
        return await getLocalProjects();
      }
    },
  });

  // Load all tasks for filtering & stats
  const { data: allTasks, refetch: refetchTasks } = useQuery<TaskOut[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      try {
        return await apiClient<TaskOut[]>('/api/tasks');
      } catch {
        return await getLocalTasks();
      }
    },
  });

  // Load all notes for filtering & stats
  const { data: allNotes, refetch: refetchNotes } = useQuery<NoteOut[]>({
    queryKey: ['notes'],
    queryFn: async () => {
      try {
        return await apiClient<NoteOut[]>('/api/notes');
      } catch {
        return await getLocalNotes();
      }
    },
  });

  // Create Project Mutation
  const createProjectMutation = useMutation({
    mutationFn: async () => {
      const payload = { title: title.trim(), description: description.trim() || undefined, status: 'active' };
      try {
        return await apiClient<ProjectOut>('/api/projects', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      } catch {
        return await saveLocalProject(payload);
      }
    },
    onSuccess: (newProj) => {
      setTitle('');
      setDescription('');
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
      // Automatically open the new project drilldown to immediately add tasks!
      setSelectedProject(newProj);
    },
    onError: (err: any) => {
      Alert.alert('Project Creation Failed', err.message);
    },
  });

  // Delete Project Mutation
  const deleteProjectMutation = useMutation({
    mutationFn: async (id: number) => {
      try {
        await apiClient(`/api/projects/${id}`, { method: 'DELETE' });
      } catch {
        // Fallback local deletion
      }
      await deleteLocalProject(id);
    },
    onSuccess: () => {
      if (selectedProject) setSelectedProject(null);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
  });

  // Toggle Project Status
  const toggleProjectStatus = async (proj: ProjectOut) => {
    const newStatus = proj.status === 'completed' ? 'active' : 'completed';
    try {
      await apiClient(`/api/projects/${proj.id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
    } catch {
      await updateLocalProject(proj.id, { status: newStatus });
    }
    const updated = { ...proj, status: newStatus };
    setSelectedProject(updated);
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  };

  // Add Task to Selected Project
  const handleAddTaskToProject = async () => {
    if (!newTaskTitle.trim() || !selectedProject) return;
    const taskTitle = newTaskTitle.trim();
    try {
      await apiClient<TaskOut>('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
          title: taskTitle,
          project_id: selectedProject.id,
          status: 'pending',
        }),
      });
    } catch {
      await saveLocalTask({
        title: taskTitle,
        project_id: selectedProject.id,
        status: 'pending',
      });
    }
    setNewTaskTitle('');
    refetchTasks();
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
    queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
  };

  // Toggle Nested Task Status
  const handleToggleTask = async (task: TaskOut) => {
    const newStatus = task.status === 'completed' ? 'pending' : 'completed';
    try {
      await apiClient(`/api/tasks/${task.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
    } catch {
      await updateLocalTask(task.id, { status: newStatus });
    }
    refetchTasks();
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
  };

  // Delete Nested Task
  const handleDeleteTask = async (taskId: number) => {
    try {
      await apiClient(`/api/tasks/${taskId}`, { method: 'DELETE' });
    } catch {
      await deleteLocalTask(taskId);
    }
    refetchTasks();
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
  };

  // Add Note to Selected Project
  const handleAddNoteToProject = async () => {
    if (!newNoteTitle.trim() || !selectedProject) return;
    const notePayload = {
      title: newNoteTitle.trim(),
      content: newNoteContent.trim(),
      project_id: selectedProject.id,
      tags: `project-${selectedProject.id}`,
    };
    try {
      await apiClient<NoteOut>('/api/notes', {
        method: 'POST',
        body: JSON.stringify(notePayload),
      });
    } catch {
      await saveLocalNote(notePayload);
    }
    setNewNoteTitle('');
    setNewNoteContent('');
    setShowAddNoteForm(false);
    refetchNotes();
    queryClient.invalidateQueries({ queryKey: ['notes'] });
    queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
  };

  // Delete Nested Note
  const handleDeleteNote = async (noteId: number) => {
    try {
      await apiClient(`/api/notes/${noteId}`, { method: 'DELETE' });
    } catch {
      await deleteLocalNote(noteId);
    }
    refetchNotes();
    queryClient.invalidateQueries({ queryKey: ['notes'] });
  };

  const confirmDelete = (item: ProjectOut) => {
    Alert.alert(
      'Delete Project',
      `Delete '${item.title}' and all its local references?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => deleteProjectMutation.mutate(item.id) },
      ]
    );
  };

  // Filtered project list
  const filteredProjects = (projects || []).filter((p) => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'active' && p.status !== 'completed') ||
      (filter === 'completed' && p.status === 'completed');
    const matchesSearch =
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  // Current project nested items
  const nestedTasks = selectedProject
    ? (allTasks || []).filter((t) => t.project_id === selectedProject.id)
    : [];
  const nestedNotes = selectedProject
    ? (allNotes || []).filter((n) => n.project_id === selectedProject.id)
    : [];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      {/* Top Bar */}
      <View style={styles.topBar}>
        <Button
          title=""
          variant="outline"
          icon={<ArrowLeft size={20} color={colors.textPrimary} />}
          onPress={() => router.back()}
          style={styles.backBtn}
        />
        <View style={styles.titleContainer}>
          <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Projects</Text>
          <Text style={[styles.topSubtitle, { color: colors.textMuted }]}>
            Sovereign Workspaces & Initiatives
          </Text>
        </View>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {/* Filter Tabs & Search Bar */}
      <View style={styles.toolbar}>
        <View style={[styles.filterGroup, { backgroundColor: colors.surfaceSubtle }]}>
          {(['all', 'active', 'completed'] as const).map((tab) => (
            <TouchableOpacity
              key={tab}
              style={[
                styles.filterTab,
                filter === tab && [styles.filterTabActive, { backgroundColor: colors.surface }],
              ]}
              onPress={() => setFilter(tab)}
            >
              <Text
                style={[
                  styles.filterTabText,
                  { color: filter === tab ? colors.primary : colors.textSecondary },
                ]}
              >
                {tab.toUpperCase()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={[styles.searchBox, { backgroundColor: colors.surface, borderColor: colors.surfaceBorder }]}>
          <Search size={14} color={colors.textMuted} />
          <TextInput
            placeholder="Search projects..."
            placeholderTextColor={colors.textMuted}
            value={search}
            onChangeText={setSearch}
            style={[styles.searchInput, { color: colors.textPrimary }]}
          />
        </View>
      </View>

      {/* Create Project Card */}
      {showAdd && (
        <Card style={styles.createCard}>
          <Input value={title} onChangeText={setTitle} placeholder="Project title..." autoFocus />
          <Input
            value={description}
            onChangeText={setDescription}
            placeholder="Objectives, scope, and key deliverables..."
            multiline
            style={{ height: 64 }}
          />
          <Button
            title="Create Project & Add Tasks"
            onPress={() => createProjectMutation.mutate()}
            loading={createProjectMutation.isPending}
            style={{ marginTop: 8 }}
          />
        </Card>
      )}

      {/* Project List */}
      <FlatList
        data={filteredProjects}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={() => {
          refetch();
          refetchTasks();
          refetchNotes();
        }}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Sovereign Projects Found"
              description="Create top-level project workspaces to organize tasks, notes, and milestones."
              icon={<FolderGit2 size={40} color={colors.textMuted} />}
              action={<Button title="Create New Project" onPress={() => setShowAdd(true)} />}
            />
          ) : undefined
        }
        renderItem={({ item }) => {
          const projectTaskCount = (allTasks || []).filter((t) => t.project_id === item.id).length;
          const projectNoteCount = (allNotes || []).filter((n) => n.project_id === item.id).length;
          const isDone = item.status === 'completed';

          return (
            <TouchableOpacity
              activeOpacity={0.8}
              onPress={() => setSelectedProject(item)}
            >
              <Card style={styles.projectCard}>
                <View style={styles.row}>
                  <View style={[styles.iconBox, { backgroundColor: isDone ? colors.surfaceSubtle : colors.accentSubtle }]}>
                    <FolderGit2 size={20} color={isDone ? colors.textMuted : colors.accent} />
                  </View>

                  <View style={styles.info}>
                    <View style={styles.cardHeaderRow}>
                      <Text style={[styles.titleText, { color: colors.textPrimary }, isDone && styles.completedText]}>
                        {item.title}
                      </Text>
                      <View
                        style={[
                          styles.badge,
                          { backgroundColor: isDone ? colors.surfaceSubtle : colors.primarySubtle },
                        ]}
                      >
                        <Text
                          style={[
                            styles.badgeText,
                            { color: isDone ? colors.textMuted : colors.primary },
                          ]}
                        >
                          {item.status ? item.status.replace('_', ' ').toUpperCase() : 'ACTIVE'}
                        </Text>
                      </View>
                    </View>

                    {item.description ? (
                      <Text style={[styles.descText, { color: colors.textSecondary }]} numberOfLines={2}>
                        {item.description}
                      </Text>
                    ) : null}

                    {/* Stats Pill Row */}
                    <View style={styles.statsRow}>
                      <View style={[styles.statPill, { backgroundColor: colors.surfaceSubtle }]}>
                        <CheckSquare size={12} color={colors.primary} />
                        <Text style={[styles.statText, { color: colors.textSecondary }]}>
                          {projectTaskCount} {projectTaskCount === 1 ? 'Task' : 'Tasks'}
                        </Text>
                      </View>
                      <View style={[styles.statPill, { backgroundColor: colors.surfaceSubtle }]}>
                        <FileText size={12} color={colors.success} />
                        <Text style={[styles.statText, { color: colors.textSecondary }]}>
                          {projectNoteCount} {projectNoteCount === 1 ? 'Note' : 'Notes'}
                        </Text>
                      </View>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={styles.delBtn}
                    onPress={() => confirmDelete(item)}
                  >
                    <Trash2 size={16} color={colors.danger} />
                  </TouchableOpacity>
                </View>
              </Card>
            </TouchableOpacity>
          );
        }}
      />

      {/* Project Drilldown Modal */}
      {selectedProject && (
        <Modal
          visible={Boolean(selectedProject)}
          animationType="slide"
          presentationStyle="pageSheet"
          onRequestClose={() => setSelectedProject(null)}
        >
          <SafeAreaView style={[styles.modalContainer, { backgroundColor: colors.background }]}>
            {/* Modal Header */}
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                    {selectedProject.title}
                  </Text>
                </View>
                <Text style={[styles.modalSubtitle, { color: colors.textMuted }]}>
                  Project #{selectedProject.id} · {selectedProject.status?.toUpperCase() || 'ACTIVE'}
                </Text>
              </View>

              <TouchableOpacity
                style={[styles.closeBtn, { backgroundColor: colors.surfaceSubtle }]}
                onPress={() => setSelectedProject(null)}
              >
                <X size={20} color={colors.textPrimary} />
              </TouchableOpacity>
            </View>

            <ScrollView contentContainerStyle={styles.modalContent}>
              {/* Description & Status Bar */}
              <Card style={styles.drilldownCard}>
                {selectedProject.description ? (
                  <Text style={[styles.drilldownDesc, { color: colors.textSecondary }]}>
                    {selectedProject.description}
                  </Text>
                ) : (
                  <Text style={[styles.drilldownDesc, { color: colors.textMuted, fontStyle: 'italic' }]}>
                    No project description provided.
                  </Text>
                )}

                <View style={[styles.divider, { backgroundColor: colors.surfaceBorder }]} />

                <View style={styles.statusActionRow}>
                  <Text style={[styles.statusLabel, { color: colors.textMuted }]}>PROJECT STATUS</Text>
                  <Button
                    title={selectedProject.status === 'completed' ? 'Mark Active' : 'Mark Completed'}
                    variant={selectedProject.status === 'completed' ? 'outline' : 'secondary'}
                    onPress={() => toggleProjectStatus(selectedProject)}
                    style={{ paddingVertical: 6, paddingHorizontal: 12 }}
                  />
                </View>
              </Card>

              {/* Tasks Section */}
              <View style={styles.sectionHeader}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <CheckSquare size={18} color={colors.primary} />
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                    Tasks ({nestedTasks.length})
                  </Text>
                </View>
              </View>

              {/* Add Task Input directly into Project */}
              <View style={[styles.inlineAddBox, { backgroundColor: colors.surface, borderColor: colors.surfaceBorder }]}>
                <TextInput
                  placeholder="Add a task under this project..."
                  placeholderTextColor={colors.textMuted}
                  value={newTaskTitle}
                  onChangeText={setNewTaskTitle}
                  style={[styles.inlineInput, { color: colors.textPrimary }]}
                  onSubmitEditing={handleAddTaskToProject}
                />
                <Button
                  title="Add"
                  icon={<Plus size={14} color="#FFF" />}
                  onPress={handleAddTaskToProject}
                  style={styles.inlineAddBtn}
                />
              </View>

              {/* Tasks List */}
              {nestedTasks.length === 0 ? (
                <View style={styles.emptyNestedBox}>
                  <Text style={[styles.emptyNestedText, { color: colors.textMuted }]}>
                    No tasks created for this project yet. Use the field above to add your first task!
                  </Text>
                </View>
              ) : (
                nestedTasks.map((t) => {
                  const done = t.status === 'completed';
                  return (
                    <View
                      key={t.id}
                      style={[
                        styles.taskRow,
                        { backgroundColor: colors.surface, borderColor: colors.surfaceBorder },
                      ]}
                    >
                      <TouchableOpacity
                        style={styles.checkTouch}
                        onPress={() => handleToggleTask(t)}
                      >
                        {done ? (
                          <CheckCircle size={20} color={colors.success} />
                        ) : (
                          <Circle size={20} color={colors.textMuted} />
                        )}
                      </TouchableOpacity>
                      <Text
                        style={[
                          styles.taskTitle,
                          { color: colors.textPrimary },
                          done && styles.completedText,
                        ]}
                      >
                        {t.title}
                      </Text>
                      <TouchableOpacity
                        onPress={() => handleDeleteTask(t.id)}
                        style={styles.delIconBtn}
                      >
                        <Trash2 size={16} color={colors.danger} />
                      </TouchableOpacity>
                    </View>
                  );
                })
              )}

              {/* Notes Section */}
              <View style={[styles.sectionHeader, { marginTop: 24 }]}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <FileText size={18} color={colors.success} />
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                    Notes & Documentation ({nestedNotes.length})
                  </Text>
                </View>
                <Button
                  title={showAddNoteForm ? 'Cancel' : '+ Note'}
                  variant="outline"
                  onPress={() => setShowAddNoteForm(!showAddNoteForm)}
                  style={{ paddingVertical: 4, paddingHorizontal: 10 }}
                />
              </View>

              {showAddNoteForm && (
                <Card style={styles.addNoteCard}>
                  <Input
                    placeholder="Note title..."
                    value={newNoteTitle}
                    onChangeText={setNewNoteTitle}
                  />
                  <Input
                    placeholder="Document thoughts, research, architecture..."
                    value={newNoteContent}
                    onChangeText={setNewNoteContent}
                    multiline
                    style={{ height: 70 }}
                  />
                  <Button
                    title="Attach Note to Project"
                    onPress={handleAddNoteToProject}
                    style={{ marginTop: 6 }}
                  />
                </Card>
              )}

              {/* Notes List */}
              {nestedNotes.length === 0 ? (
                <View style={styles.emptyNestedBox}>
                  <Text style={[styles.emptyNestedText, { color: colors.textMuted }]}>
                    No notes attached to this project. Keep project documentation organized right here!
                  </Text>
                </View>
              ) : (
                nestedNotes.map((n) => (
                  <Card key={n.id} style={styles.noteMiniCard}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Text style={[styles.noteMiniTitle, { color: colors.textPrimary }]}>{n.title}</Text>
                      <TouchableOpacity onPress={() => handleDeleteNote(n.id)}>
                        <Trash2 size={14} color={colors.danger} />
                      </TouchableOpacity>
                    </View>
                    <Text style={[styles.noteMiniContent, { color: colors.textSecondary }]}>{n.content}</Text>
                  </Card>
                ))
              )}
            </ScrollView>
          </SafeAreaView>
        </Modal>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  backBtn: {
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  titleContainer: {
    flex: 1,
  },
  topTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  topSubtitle: {
    fontSize: 12,
  },
  addBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  toolbar: {
    paddingHorizontal: 16,
    marginBottom: 8,
    gap: 8,
  },
  filterGroup: {
    flexDirection: 'row',
    borderRadius: 8,
    padding: 3,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 6,
    alignItems: 'center',
    borderRadius: 6,
  },
  filterTabActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  filterTabText: {
    fontSize: 11,
    fontWeight: '700',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    height: 38,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 13,
    padding: 0,
  },
  createCard: {
    marginHorizontal: 16,
    marginBottom: 12,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  projectCard: {
    marginBottom: 10,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  iconBox: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  info: {
    flex: 1,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  titleText: {
    fontSize: 16,
    fontWeight: '700',
    flex: 1,
  },
  completedText: {
    textDecorationLine: 'line-through',
    opacity: 0.6,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  descText: {
    fontSize: 12,
    marginTop: 4,
    lineHeight: 16,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  statPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  statText: {
    fontSize: 11,
    fontWeight: '600',
  },
  delBtn: {
    padding: 6,
    marginLeft: 4,
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  modalSubtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalContent: {
    padding: 20,
    paddingBottom: 40,
  },
  drilldownCard: {
    marginBottom: 20,
  },
  drilldownDesc: {
    fontSize: 14,
    lineHeight: 20,
  },
  divider: {
    height: 1,
    marginVertical: 12,
  },
  statusActionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusLabel: {
    fontSize: 11,
    fontWeight: '700',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  inlineAddBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    paddingLeft: 12,
    paddingRight: 4,
    height: 44,
    marginBottom: 12,
  },
  inlineInput: {
    flex: 1,
    fontSize: 13,
  },
  inlineAddBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  emptyNestedBox: {
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.02)',
    marginBottom: 12,
  },
  emptyNestedText: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    gap: 10,
  },
  checkTouch: {
    padding: 2,
  },
  taskTitle: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
  },
  delIconBtn: {
    padding: 4,
  },
  addNoteCard: {
    padding: 12,
    marginBottom: 12,
  },
  noteMiniCard: {
    marginBottom: 8,
    padding: 12,
  },
  noteMiniTitle: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 4,
  },
  noteMiniContent: {
    fontSize: 12,
    lineHeight: 16,
  },
});
