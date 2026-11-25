import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  TextInput,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Plus,
  CheckCircle,
  Circle,
  Trash2,
  CheckSquare,
  Search,
  FolderGit2,
} from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { TaskOut, ProjectOut } from '../../../src/api/types';
import {
  getLocalTasks,
  saveLocalTask,
  updateLocalTask,
  deleteLocalTask,
  cacheRemoteTasks,
  getLocalProjects,
} from '../../../src/api/workspaceStore';

export default function TasksScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all');
  const [search, setSearch] = useState('');

  // Fetch tasks
  const { data: tasks, isLoading, refetch } = useQuery<TaskOut[]>({
    queryKey: ['tasks'],
    queryFn: async () => {
      try {
        const remote = await apiClient<TaskOut[]>('/api/tasks');
        await cacheRemoteTasks(remote);
        return remote;
      } catch {
        return await getLocalTasks();
      }
    },
  });

  // Fetch projects for assignment & badge rendering
  const { data: projects } = useQuery<ProjectOut[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      try {
        return await apiClient<ProjectOut[]>('/api/projects');
      } catch {
        return await getLocalProjects();
      }
    },
  });

  const projectMap = new Map<number, string>();
  (projects || []).forEach((p) => projectMap.set(p.id, p.title));

  const createTaskMutation = useMutation({
    mutationFn: async ({ title, projectId }: { title: string; projectId: number | null }) => {
      const payload = {
        title,
        project_id: projectId,
        status: 'pending' as const,
      };
      try {
        return await apiClient<TaskOut>('/api/tasks', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      } catch {
        return await saveLocalTask(payload);
      }
    },
    onSuccess: () => {
      setNewTaskTitle('');
      setSelectedProjectId(null);
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
    onError: (err: any) => {
      Alert.alert('Task Creation Failed', err.message);
    },
  });

  const toggleTaskMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: 'pending' | 'in_progress' | 'completed' | 'cancelled' }) => {
      try {
        return await apiClient<TaskOut>(`/api/tasks/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({ status }),
        });
      } catch {
        return await updateLocalTask(id, { status });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: async (id: number) => {
      try {
        await apiClient(`/api/tasks/${id}`, { method: 'DELETE' });
      } catch {
        // Fallback local deletion
      }
      await deleteLocalTask(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
  });

  const submitNewTask = () => {
    if (!newTaskTitle.trim()) return;
    createTaskMutation.mutate({
      title: newTaskTitle.trim(),
      projectId: selectedProjectId,
    });
  };

  const filteredTasks = (tasks || []).filter((t) => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'pending' && t.status === 'pending') ||
      (filter === 'in_progress' && t.status === 'in_progress') ||
      (filter === 'completed' && t.status === 'completed');
    const matchesSearch = t.title.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

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
          <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Tasks & Objectives</Text>
          <Text style={[styles.topSubtitle, { color: colors.textMuted }]}>
            Sovereign Action Items & Deadlines
          </Text>
        </View>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {/* Toolbar: Status Filter Tabs & Search */}
      <View style={styles.toolbar}>
        <View style={[styles.filterGroup, { backgroundColor: colors.surfaceSubtle }]}>
          {(
            [
              { id: 'all', label: 'ALL' },
              { id: 'pending', label: 'PENDING' },
              { id: 'in_progress', label: 'IN PROGRESS' },
              { id: 'completed', label: 'DONE' },
            ] as const
          ).map((tab) => (
            <TouchableOpacity
              key={tab.id}
              style={[
                styles.filterTab,
                filter === tab.id && [styles.filterTabActive, { backgroundColor: colors.surface }],
              ]}
              onPress={() => setFilter(tab.id)}
            >
              <Text
                style={[
                  styles.filterTabText,
                  { color: filter === tab.id ? colors.primary : colors.textSecondary },
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={[styles.searchBox, { backgroundColor: colors.surface, borderColor: colors.surfaceBorder }]}>
          <Search size={14} color={colors.textMuted} />
          <TextInput
            placeholder="Search tasks..."
            placeholderTextColor={colors.textMuted}
            value={search}
            onChangeText={setSearch}
            style={[styles.searchInput, { color: colors.textPrimary }]}
          />
        </View>
      </View>

      {/* Create Task Card */}
      {showAdd && (
        <Card style={styles.createBox}>
          <Input
            value={newTaskTitle}
            onChangeText={setNewTaskTitle}
            placeholder="What needs to be accomplished?"
            autoFocus
          />

          {/* Project Picker */}
          {projects && projects.length > 0 && (
            <View style={styles.projectPickerSection}>
              <Text style={[styles.projectPickerLabel, { color: colors.textMuted }]}>
                ASSIGN TO PROJECT
              </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.projectPillsRow}>
                <TouchableOpacity
                  style={[
                    styles.projectPill,
                    selectedProjectId === null && [styles.projectPillActive, { backgroundColor: colors.primary }],
                    { borderColor: colors.surfaceBorder },
                  ]}
                  onPress={() => setSelectedProjectId(null)}
                >
                  <Text
                    style={[
                      styles.projectPillText,
                      { color: selectedProjectId === null ? '#FFF' : colors.textSecondary },
                    ]}
                  >
                    No Project
                  </Text>
                </TouchableOpacity>

                {projects.map((p) => {
                  const isSelected = selectedProjectId === p.id;
                  return (
                    <TouchableOpacity
                      key={p.id}
                      style={[
                        styles.projectPill,
                        isSelected && [styles.projectPillActive, { backgroundColor: colors.primary }],
                        { borderColor: colors.surfaceBorder },
                      ]}
                      onPress={() => setSelectedProjectId(p.id)}
                    >
                      <FolderGit2 size={12} color={isSelected ? '#FFF' : colors.textMuted} />
                      <Text
                        style={[
                          styles.projectPillText,
                          { color: isSelected ? '#FFF' : colors.textSecondary },
                        ]}
                      >
                        {p.title}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>
          )}

          <Button
            title="Create Objective"
            onPress={submitNewTask}
            loading={createTaskMutation.isPending}
            style={{ marginTop: 8 }}
          />
        </Card>
      )}

      {/* Task List */}
      <FlatList
        data={filteredTasks}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Tasks Found"
              description="Keep track of your day-to-day action items, project deliverables, and deadlines."
              icon={<CheckSquare size={40} color={colors.textMuted} />}
              action={<Button title="Add New Task" onPress={() => setShowAdd(true)} />}
            />
          ) : undefined
        }
        renderItem={({ item }) => {
          const isDone = item.status === 'completed';
          const projectName = item.project_id ? projectMap.get(item.project_id) : null;

          return (
            <Card style={styles.taskCard}>
              <View style={styles.cardRow}>
                <TouchableOpacity
                  style={styles.checkButton}
                  onPress={() =>
                    toggleTaskMutation.mutate({
                      id: item.id,
                      status: isDone ? 'pending' : 'completed',
                    })
                  }
                >
                  {isDone ? (
                    <CheckCircle size={22} color={colors.success} />
                  ) : (
                    <Circle size={22} color={colors.textMuted} />
                  )}
                </TouchableOpacity>

                <View style={styles.taskContent}>
                  <Text
                    style={[
                      styles.taskTitle,
                      { color: colors.textPrimary },
                      isDone && styles.completedTitle,
                    ]}
                  >
                    {item.title}
                  </Text>

                  <View style={styles.metaRow}>
                    {projectName && (
                      <View style={[styles.projectTag, { backgroundColor: colors.accentSubtle }]}>
                        <FolderGit2 size={11} color={colors.accent} />
                        <Text style={[styles.projectTagText, { color: colors.accent }]} numberOfLines={1}>
                          {projectName}
                        </Text>
                      </View>
                    )}

                    <View
                      style={[
                        styles.statusTag,
                        {
                          backgroundColor:
                            item.status === 'completed'
                              ? colors.surfaceSubtle
                              : item.status === 'in_progress'
                              ? colors.warningSubtle
                              : colors.primarySubtle,
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.statusTagText,
                          {
                            color:
                              item.status === 'completed'
                                ? colors.textMuted
                                : item.status === 'in_progress'
                                ? colors.warning
                                : colors.primary,
                          },
                        ]}
                      >
                        {item.status.replace('_', ' ').toUpperCase()}
                      </Text>
                    </View>
                  </View>
                </View>

                <TouchableOpacity
                  style={styles.delBtn}
                  onPress={() => {
                    Alert.alert('Delete Task', `Delete "${item.title}"?`, [
                      { text: 'Cancel', style: 'cancel' },
                      { text: 'Delete', style: 'destructive', onPress: () => deleteTaskMutation.mutate(item.id) },
                    ]);
                  }}
                >
                  <Trash2 size={16} color={colors.danger} />
                </TouchableOpacity>
              </View>
            </Card>
          );
        }}
      />
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
    fontSize: 10,
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
  createBox: {
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 12,
  },
  projectPickerSection: {
    marginTop: 8,
    marginBottom: 4,
  },
  projectPickerLabel: {
    fontSize: 10,
    fontWeight: '700',
    marginBottom: 6,
  },
  projectPillsRow: {
    flexDirection: 'row',
    gap: 6,
  },
  projectPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
  },
  projectPillActive: {
    borderColor: 'transparent',
  },
  projectPillText: {
    fontSize: 11,
    fontWeight: '600',
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  taskCard: {
    marginBottom: 8,
    padding: 12,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkButton: {
    padding: 2,
  },
  taskContent: {
    flex: 1,
  },
  taskTitle: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 20,
  },
  completedTitle: {
    textDecorationLine: 'line-through',
    opacity: 0.5,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 6,
  },
  projectTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    maxWidth: 160,
  },
  projectTagText: {
    fontSize: 10,
    fontWeight: '700',
  },
  statusTag: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusTagText: {
    fontSize: 9,
    fontWeight: '800',
  },
  delBtn: {
    padding: 6,
  },
});
