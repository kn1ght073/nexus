import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, FolderGit2 } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { ProjectOut } from '../../../src/api/types';

export default function ProjectsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const { data: projects, isLoading, refetch } = useQuery<ProjectOut[]>({
    queryKey: ['projects'],
    queryFn: () => apiClient<ProjectOut[]>('/api/projects'),
  });

  const createProjectMutation = useMutation({
    mutationFn: () =>
      apiClient<ProjectOut>('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), description: description.trim() }),
      }),
    onSuccess: () => {
      setTitle('');
      setDescription('');
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
    onError: (err: any) => {
      Alert.alert('Project Creation Failed', err.message);
    },
  });

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
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Projects</Text>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {showAdd && (
        <Card style={styles.createCard}>
          <Input value={title} onChangeText={setTitle} placeholder="Project title..." />
          <Input
            value={description}
            onChangeText={setDescription}
            placeholder="Objectives and scope..."
            multiline
            style={{ height: 60 }}
          />
          <Button
            title="Create Project"
            onPress={() => createProjectMutation.mutate()}
            loading={createProjectMutation.isPending}
            style={{ marginTop: 8 }}
          />
        </Card>
      )}

      <FlatList
        data={projects || []}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Sovereign Projects"
              description="Group your tasks, research, and documentation into organized project workspaces."
              icon={<FolderGit2 size={40} color={colors.textMuted} />}
              action={<Button title="Create Project" onPress={() => setShowAdd(true)} />}
            />
          ) : undefined
        }
        renderItem={({ item }) => (
          <Card style={styles.projectCard}>
            <View style={styles.row}>
              <View style={[styles.iconBox, { backgroundColor: colors.accentSubtle }]}>
                <FolderGit2 size={20} color={colors.accent} />
              </View>
              <View style={styles.info}>
                <Text style={[styles.titleText, { color: colors.textPrimary }]}>{item.title}</Text>
                {item.description && (
                  <Text style={[styles.descText, { color: colors.textSecondary }]} numberOfLines={2}>
                    {item.description}
                  </Text>
                )}
              </View>
            </View>
          </Card>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  backBtn: { width: 44, height: 44, paddingHorizontal: 0, paddingVertical: 0, borderRadius: 12 },
  addBtn: { width: 44, height: 44, paddingHorizontal: 0, paddingVertical: 0, borderRadius: 12 },
  topTitle: { fontSize: 18, fontWeight: '700' },
  createCard: { marginHorizontal: 20, marginBottom: 12 },
  list: { padding: 20, paddingTop: 4 },
  projectCard: { marginBottom: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconBox: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  info: { flex: 1 },
  titleText: { fontSize: 16, fontWeight: '700' },
  descText: { fontSize: 12, marginTop: 2, lineHeight: 16 },
});
