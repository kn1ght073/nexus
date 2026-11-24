import React from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Shield, Smartphone, Server, CheckSquare, FolderGit2, QrCode, Activity } from 'lucide-react-native';
import { useTheme } from '../../src/context/ThemeContext';
import { useAuth } from '../../src/context/AuthContext';
import { Card } from '../../src/components/Card';
import { Button } from '../../src/components/Button';
import { StatusBadge } from '../../src/components/StatusBadge';
import { MetricBox } from '../../src/components/MetricBox';
import { apiClient } from '../../src/api/client';
import { AccountOverviewResponse, ActiveNodeResponse, ActivityEvent } from '../../src/api/types';

export default function CockpitDashboard() {
  const { colors } = useTheme();
  const { account, refreshAccount, serverUrl } = useAuth();
  const router = useRouter();

  const { data: activeNodeData, refetch: refetchNode } = useQuery<ActiveNodeResponse>({
    queryKey: ['activeNode'],
    queryFn: () => apiClient<ActiveNodeResponse>('/api/nodes/active'),
  });

  const { data: recentActivity, refetch: refetchActivity, isRefetching } = useQuery<ActivityEvent[]>({
    queryKey: ['recentActivity'],
    queryFn: () => apiClient<ActivityEvent[]>('/api/account/activity?limit=5'),
  });

  const onRefresh = async () => {
    await Promise.all([refreshAccount(), refetchNode(), refetchActivity()]);
  };

  const activeNode = activeNodeData?.active_node;
  const metrics = account?.metrics || { projects: 0, tasks: 0, notes: 0, files: 0 };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        {/* Top Header */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.greeting, { color: colors.textMuted }]}>SOVEREIGN COCKPIT</Text>
            <Text style={[styles.userName, { color: colors.textPrimary }]}>
              {account?.google_identity?.name || account?.display_name || account?.email || 'NEXUS Operator'}
            </Text>
          </View>
          <StatusBadge status="online" label="CONTROL PLANE" />
        </View>

        {/* Server Endpoint Bar */}
        <View style={[styles.endpointBar, { backgroundColor: colors.surfaceSubtle, borderColor: colors.surfaceBorder }]}>
          <Shield size={14} color={colors.primary} />
          <Text style={[styles.endpointText, { color: colors.textSecondary }]} numberOfLines={1}>
            {serverUrl}
          </Text>
        </View>

        {/* Node Liveness Card */}
        <Card style={styles.card}>
          <View style={styles.cardTop}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Server size={18} color={colors.primary} />
              <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Active Edge Node</Text>
            </View>
            <StatusBadge status={activeNode?.is_online ? 'online' : 'offline'} />
          </View>

          {activeNode ? (
            <View style={styles.nodeBody}>
              <Text style={[styles.nodeName, { color: colors.textPrimary }]}>{activeNode.name}</Text>
              <Text style={[styles.nodePlatform, { color: colors.textMuted }]}>
                Platform: {activeNode.platform} · {activeNode.endpoint || 'Direct Relay Bridge'}
              </Text>
            </View>
          ) : (
            <View style={styles.nodeBody}>
              <Text style={[styles.nodeName, { color: colors.textSecondary }]}>No Edge Node Claimed</Text>
              <Text style={[styles.nodePlatform, { color: colors.textMuted }]}>
                Promote a local desktop/laptop node via `nexus node claim`
              </Text>
            </View>
          )}

          <View style={styles.actionRow}>
            <Button
              title="Pair Node"
              variant="secondary"
              icon={<QrCode size={16} color={colors.textPrimary} />}
              onPress={() => router.push('/(app)/nodes/pair')}
              style={{ flex: 1 }}
            />
            <Button
              title="View Fleet"
              variant="outline"
              onPress={() => router.push('/(app)/nodes')}
              style={{ flex: 1 }}
            />
          </View>
        </Card>

        {/* Metrics Row */}
        <View style={styles.metricsRow}>
          <MetricBox
            label="Devices"
            value={account?.device_count || 0}
            subtext="Registered"
            icon={<Smartphone size={16} color={colors.primary} />}
          />
          <MetricBox
            label="Tasks"
            value={metrics.tasks}
            subtext="Objectives"
            icon={<CheckSquare size={16} color={colors.success} />}
          />
          <MetricBox
            label="Projects"
            value={metrics.projects}
            subtext="Workspaces"
            icon={<FolderGit2 size={16} color={colors.accent} />}
          />
        </View>

        {/* Quick Operations */}
        <Card style={styles.card}>
          <Text style={[styles.sectionHeading, { color: colors.textPrimary }]}>Quick Operations</Text>
          <View style={styles.quickGrid}>
            <Button
              title="Manage Devices"
              variant="secondary"
              icon={<Smartphone size={16} color={colors.textPrimary} />}
              onPress={() => router.push('/(app)/devices')}
              style={styles.gridBtn}
            />
            <Button
              title="Tasks & Deadlines"
              variant="secondary"
              icon={<CheckSquare size={16} color={colors.textPrimary} />}
              onPress={() => router.push('/(app)/workspace/tasks')}
              style={styles.gridBtn}
            />
          </View>
        </Card>

        {/* Recent Audit Activity */}
        <Card style={styles.card}>
          <View style={styles.cardTop}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Activity size={18} color={colors.primary} />
              <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Recent Activity</Text>
            </View>
          </View>

          {recentActivity && recentActivity.length > 0 ? (
            recentActivity.map((evt) => (
              <View key={evt.id} style={[styles.activityItem, { borderBottomColor: colors.surfaceBorder }]}>
                <View>
                  <Text style={[styles.activityAction, { color: colors.textPrimary }]}>{evt.action}</Text>
                  {evt.detail && <Text style={[styles.activityDetail, { color: colors.textMuted }]}>{evt.detail}</Text>}
                </View>
                <Text style={[styles.activityTime, { color: colors.textMuted }]}>
                  {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
            ))
          ) : (
            <Text style={[styles.emptyText, { color: colors.textMuted }]}>No recent activity events recorded.</Text>
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    padding: 20,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  greeting: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1.2,
  },
  userName: {
    fontSize: 22,
    fontWeight: '800',
    marginTop: 2,
  },
  endpointBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 16,
  },
  endpointText: {
    fontSize: 12,
    fontWeight: '500',
  },
  card: {
    marginBottom: 16,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  nodeBody: {
    marginVertical: 4,
  },
  nodeName: {
    fontSize: 18,
    fontWeight: '700',
  },
  nodePlatform: {
    fontSize: 12,
    marginTop: 4,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 14,
  },
  metricsRow: {
    flexDirection: 'row',
    marginBottom: 16,
    marginHorizontal: -4,
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 12,
  },
  quickGrid: {
    gap: 10,
  },
  gridBtn: {
    justifyContent: 'flex-start',
    paddingVertical: 12,
  },
  activityItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  activityAction: {
    fontSize: 13,
    fontWeight: '600',
  },
  activityDetail: {
    fontSize: 11,
    marginTop: 2,
  },
  activityTime: {
    fontSize: 11,
  },
  emptyText: {
    fontSize: 13,
    paddingVertical: 12,
  },
});
