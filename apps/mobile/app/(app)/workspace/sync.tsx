import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw, CheckCircle2, CloudDownload, HardDrive } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Card } from '../../../src/components/Card';
import { StatusBadge } from '../../../src/components/StatusBadge';
import { apiClient } from '../../../src/api/client';
import { SyncPullResponse } from '../../../src/api/types';

export default function SyncScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [lastSyncResult, setLastSyncResult] = useState<SyncPullResponse | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  const pullMutation = useMutation({
    mutationFn: () =>
      apiClient<SyncPullResponse>('/api/sync/pull', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: (data) => {
      setLastSyncResult(data);
      setLastSyncTime(new Date().toLocaleTimeString());
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['notes'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
      Alert.alert(
        'Synchronization Complete',
        `Pulled ${data.changes.tasks.length} tasks, ${data.changes.projects.length} projects, and ${data.changes.notes.length} notes.`
      );
    },
    onError: (err: any) => {
      Alert.alert('Sync Failed', err.message);
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
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Synchronization Center</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Card style={styles.card}>
          <View style={styles.cardTop}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <RefreshCw size={18} color={colors.primary} />
              <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Delta Sync Status</Text>
            </View>
            <StatusBadge status="active" label="REVISION READY" />
          </View>

          <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
            NEXUS uses incremental delta-pull with monotonic revision counters. Only modified records are transferred over the wire.
          </Text>

          <Button
            title="Trigger Full Sync Pull"
            onPress={() => pullMutation.mutate()}
            loading={pullMutation.isPending}
            icon={<CloudDownload size={18} color="#FFFFFF" />}
            style={{ marginTop: 10 }}
          />

          {lastSyncTime && (
            <Text style={[styles.syncTime, { color: colors.textMuted }]}>
              Last synchronized at: {lastSyncTime}
            </Text>
          )}
        </Card>

        {lastSyncResult && (
          <Card style={styles.card}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary, marginBottom: 12 }]}>
              Latest Reconciled Entities
            </Text>
            <View style={styles.entityRow}>
              <Text style={[styles.entityName, { color: colors.textSecondary }]}>Projects:</Text>
              <Text style={[styles.entityVal, { color: colors.textPrimary }]}>
                {lastSyncResult.changes.projects.length}
              </Text>
            </View>
            <View style={styles.entityRow}>
              <Text style={[styles.entityName, { color: colors.textSecondary }]}>Tasks:</Text>
              <Text style={[styles.entityVal, { color: colors.textPrimary }]}>
                {lastSyncResult.changes.tasks.length}
              </Text>
            </View>
            <View style={styles.entityRow}>
              <Text style={[styles.entityName, { color: colors.textSecondary }]}>Notes:</Text>
              <Text style={[styles.entityVal, { color: colors.textPrimary }]}>
                {lastSyncResult.changes.notes.length}
              </Text>
            </View>
          </Card>
        )}

        <View style={styles.securityBox}>
          <HardDrive size={18} color={colors.primary} />
          <Text style={[styles.securityText, { color: colors.textSecondary }]}>
            Conflict resolution uses Last-Writer-Wins with stale-writer rejection. Conflicts are safely isolated.
          </Text>
        </View>
      </ScrollView>
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
  topTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  content: {
    padding: 20,
  },
  card: {
    marginBottom: 16,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 8,
  },
  syncTime: {
    fontSize: 12,
    marginTop: 10,
    textAlign: 'center',
  },
  entityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  entityName: {
    fontSize: 14,
  },
  entityVal: {
    fontSize: 14,
    fontWeight: '700',
  },
  securityBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 8,
  },
  securityText: {
    fontSize: 12,
    flex: 1,
    lineHeight: 16,
  },
});
