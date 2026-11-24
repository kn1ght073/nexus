import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, FolderGit2, HardDrive, Trash2 } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient, getLastSyncTimestamp, setLastSyncTimestamp } from '../../../src/api/client';
import { ProjectOut } from '../../../src/api/types';
import { getLocalProjects, saveLocalProject, deleteLocalProject, cacheRemoteProjects } from '../../../src/api/workspaceStore';

export default function ProjectsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  const { data: projects, isLoading, refetch } = useQuery<ProjectOut[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      try {
        const remote = await apiClient<ProjectOut[]>('/api/projects');
        setIsOffline(false);
        await cacheRemoteProjects(remote);
        const now = new Date().toISOString();
        await setLastSyncTimestamp(now);
        setLastSyncTime(now);
        return remote;
      } catch (err: any) {
        setIsOffline(true);
        const ts = await getLastSyncTimestamp();
        setLastSyncTime(ts);
        return await getLocalProjects();
      }
    },
  });

  const createProjectMutation = useMutation({
    mutationFn: async () => {
      const payload = { title: title.trim(), description: description.trim() };
      try {
        const res = await apiClient<ProjectOut>('/api/projects', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        const now = new Date().toISOString();
        await setLastSyncTimestamp(now);
        return res;
      } catch (err: any) {
        setIsOffline(true);
        return await saveLocalProject(payload);
      }
    },
    onSuccess: () => {
      setTitle('');
      setDescription('');
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
    onError: (err: any) => {
      Alert.alert('Project Creation Failed', err.message);
    },
  });

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
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const confirmDelete = (item: ProjectOut) => {
    Alert.alert(
      'Delete Project',
      `Delete '${item.title}'? This action synchronizes across all devices.`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => deleteProjectMutation.mutate(item.id) },
      ]
    );
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
        <View style={styles.titleContainer}>
          <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Projects</Text>
          <Text style={[styles.topSubtitle, { color: colors.textMuted }]}>
            Sovereign Workspaces
          </Text>
        </View>
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

      {isOffline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            ⚠️ Mac Host Disconnected · Displaying cached data
            {lastSyncTime ? ` (Last synced: ${new Date(lastSyncTime).toLocaleTimeString()})` : ''}
          </Text>
        </View>
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
                <View style={styles.cardHeaderRow}>
                  <Text style={[styles.titleText, { color: colors.textPrimary }]}>{item.title}</Text>
                  <View style={[styles.badge, { backgroundColor: colors.surfaceSubtle }]}>
                    <Text style={[styles.badgeText, { color: colors.textSecondary }]}>
                      {item.status || 'Active'}
                    </Text>
                  </View>
                </View>
                {item.description && (
                  <Text style={[styles.descText, { color: colors.textSecondary }]} numberOfLines={2}>
                    {item.description}
                  </Text>
                )}
              </View>
              <Button
                title=""
                variant="outline"
                icon={<Trash2 size={16} color={colors.danger} />}
                onPress={() => confirmDelete(item)}
                style={styles.delBtn}
              />
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
  titleContainer: { alignItems: 'center' },
  topTitle: { fontSize: 18, fontWeight: '700' },
  topSubtitle: { fontSize: 11, fontWeight: '500', marginTop: 1 },
  createCard: { marginHorizontal: 20, marginBottom: 12 },
  list: { padding: 20, paddingTop: 4 },
  projectCard: { marginBottom: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  iconBox: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  info: { flex: 1 },
  cardHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  titleText: { fontSize: 16, fontWeight: '700', flex: 1 },
  descText: { fontSize: 12, marginTop: 4, lineHeight: 16 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6, marginLeft: 8 },
  badgeText: { fontSize: 10, fontWeight: '600', textTransform: 'capitalize' },
  offlineBanner: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginHorizontal: 20,
    marginBottom: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  offlineBannerText: {
    color: '#EF4444',
    fontSize: 12,
    fontWeight: '600',
  },
  delBtn: {
    width: 36,
    height: 36,
    paddingHorizontal: 0,
    paddingVertical: 0,
    borderRadius: 8,
    marginLeft: 8,
  },
});
