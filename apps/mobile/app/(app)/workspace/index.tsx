import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { CheckSquare, FolderGit2, FileText, HardDrive, ArrowRight, RefreshCw } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Card } from '../../../src/components/Card';
import { Button } from '../../../src/components/Button';
import { apiClient } from '../../../src/api/client';
import { AccountOverviewResponse } from '../../../src/api/types';

export default function WorkspaceHub() {
  const { colors } = useTheme();
  const router = useRouter();

  const { data: account } = useQuery<AccountOverviewResponse>({
    queryKey: ['accountOverview'],
    queryFn: () => apiClient<AccountOverviewResponse>('/api/account/overview'),
  });

  const metrics = account?.metrics || { tasks: 0, projects: 0, notes: 0, files: 0 };

  const modules = [
    {
      title: 'Tasks & Objectives',
      desc: 'Daily deadlines, priority tags, and completion tracking',
      count: metrics.tasks,
      icon: <CheckSquare size={22} color={colors.primary} />,
      route: '/workspace/tasks',
    },
    {
      title: 'Projects & Workspaces',
      desc: 'Top-level initiatives and sovereign workspaces',
      count: metrics.projects,
      icon: <FolderGit2 size={22} color={colors.accent} />,
      route: '/workspace/projects',
    },
    {
      title: 'Notes & Ideas',
      desc: 'Quick thoughts, markdown notes, and tag filters',
      count: metrics.notes,
      icon: <FileText size={22} color={colors.success} />,
      route: '/workspace/notes',
    },
    {
      title: 'Storage & Files',
      desc: 'Jailed sovereign storage roots on your primary node',
      count: metrics.files,
      icon: <HardDrive size={22} color={colors.warning} />,
      route: '/workspace/files',
    },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Personal Workspace</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Sovereign data stored exclusively on your edge nodes
          </Text>
        </View>
        <Button
          title="Sync"
          variant="secondary"
          icon={<RefreshCw size={14} color={colors.textPrimary} />}
          onPress={() => router.push('/workspace/sync')}
          style={styles.syncBtn}
        />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {modules.map((m, idx) => (
          <TouchableOpacity
            key={idx}
            activeOpacity={0.8}
            onPress={() => router.push(m.route as any)}
          >
            <Card style={styles.card}>
              <View style={styles.cardRow}>
                <View style={[styles.iconBox, { backgroundColor: colors.surfaceSubtle }]}>
                  {m.icon}
                </View>
                <View style={styles.textBox}>
                  <View style={styles.titleRow}>
                    <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>{m.title}</Text>
                    <Text style={[styles.countBadge, { color: colors.primary, backgroundColor: colors.primarySubtle }]}>
                      {m.count}
                    </Text>
                  </View>
                  <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>{m.desc}</Text>
                </View>
                <ArrowRight size={18} color={colors.textMuted} />
              </View>
            </Card>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  syncBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  content: {
    padding: 20,
    gap: 12,
  },
  card: {
    marginVertical: 0,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  iconBox: {
    width: 46,
    height: 46,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textBox: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  countBadge: {
    fontSize: 12,
    fontWeight: '800',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    overflow: 'hidden',
  },
  cardDesc: {
    fontSize: 12,
    lineHeight: 16,
  },
});
