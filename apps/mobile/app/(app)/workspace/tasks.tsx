import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, CheckCircle, Circle, Trash2, Calendar } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { TaskOut } from '../../../src/api/types';

export default function TasksScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const { data: tasks, isLoading, refetch } = useQuery<TaskOut[]>({
    queryKey: ['tasks'],
    queryFn: () => apiClient<TaskOut[]>('/api/tasks'),
  });

  const createTaskMutation = useMutation({
    mutationFn: (title: string) =>
      apiClient<TaskOut>('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({ title, status: 'pending' }),
      }),
    onSuccess: () => {
      setNewTaskTitle('');
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (err: any) => {
      Alert.alert('Task Creation Failed', err.message);
    },
  });

  const toggleTaskMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      apiClient<TaskOut>(`/api/tasks/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: (id: number) => apiClient(`/api/tasks/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const submitNewTask = () => {
    if (!newTaskTitle.trim()) return;
    createTaskMutation.mutate(newTaskTitle.trim());
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.topBar}>
        <Button
          title=""
          variant="outline"
          icon={<ArrowLeft size={20} color={colors.textPrimary} />}
          onPress={() => router.back()}
          style={styles.backBtn}
        />
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Tasks & Objectives</Text>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {showAdd && (
        <View style={styles.createBox}>
          <Input
            value={newTaskTitle}
            onChangeText={setNewTaskTitle}
            placeholder="What needs to be accomplished?"
            autoFocus
          />
          <Button
            title="Add Objective"
            onPress={submitNewTask}
            loading={createTaskMutation.isPending}
            style={{ marginTop: 6 }}
          />
        </View>
      )}

      <FlatList
        data={tasks || []}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Sovereign Tasks"
              description="Stay productive by creating your first personal objective."
              action={
                <Button
                  title="Create Task"
                  onPress={() => setShowAdd(true)}
                />
              }
            />
          ) : null
        }
        renderItem={({ item }) => {
          const isDone = item.status === 'completed';
          return (
            <Card style={styles.taskCard}>
              <View style={styles.taskRow}>
                <TouchableOpacity
                  onPress={() =>
                    toggleTaskMutation.mutate({
                      id: item.id,
                      status: isDone ? 'pending' : 'completed',
                    })
                  }
                  style={styles.checkTouch}
                >
                  {isDone ? (
                    <CheckCircle size={22} color={colors.success} />
                  ) : (
                    <Circle size={22} color={colors.textMuted} />
                  )}
                </TouchableOpacity>

                <View style={styles.taskInfo}>
                  <Text
                    style={[
                      styles.taskTitle,
                      {
                        color: isDone ? colors.textMuted : colors.textPrimary,
                        textDecorationLine: isDone ? 'line-through' : 'none',
                      },
                    ]}
                  >
                    {item.title}
                  </Text>
                  {item.due_date && (
                    <View style={styles.metaRow}>
                      <Calendar size={12} color={colors.textMuted} />
                      <Text style={[styles.metaText, { color: colors.textMuted }]}>
                        {new Date(item.due_date).toLocaleDateString()}
                      </Text>
                    </View>
                  )}
                </View>

                <TouchableOpacity
                  onPress={() => deleteTaskMutation.mutate(item.id)}
                  style={styles.delTouch}
                >
                  <Trash2 size={16} color={colors.textMuted} />
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
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  backBtn: {
    width: 44,
    height: 44,
    paddingHorizontal: 0,
    paddingVertical: 0,
    borderRadius: 12,
  },
  addBtn: {
    width: 44,
    height: 44,
    paddingHorizontal: 0,
    paddingVertical: 0,
    borderRadius: 12,
  },
  topTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  createBox: {
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  list: {
    padding: 20,
    paddingTop: 4,
  },
  taskCard: {
    marginVertical: 4,
    paddingVertical: 12,
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkTouch: {
    padding: 2,
  },
  taskInfo: {
    flex: 1,
  },
  taskTitle: {
    fontSize: 15,
    fontWeight: '600',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  metaText: {
    fontSize: 11,
  },
  delTouch: {
    padding: 6,
  },
});
