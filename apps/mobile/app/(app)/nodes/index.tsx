import React from 'react';
import { View, Text, StyleSheet, FlatList } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Server, QrCode } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Card } from '../../../src/components/Card';
import { Button } from '../../../src/components/Button';
import { StatusBadge } from '../../../src/components/StatusBadge';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { NodeOut } from '../../../src/api/types';

export default function NodesScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  const { data: nodes, isLoading, refetch } = useQuery<NodeOut[]>({
    queryKey: ['nodes'],
    queryFn: () => apiClient<NodeOut[]>('/api/nodes'),
  });

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Edge Nodes</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Claimed sovereign servers and compute nodes
          </Text>
        </View>
        <Button
          title="Pair"
          icon={<QrCode size={16} color="#FFFFFF" />}
          onPress={() => router.push('/nodes/pair')}
          style={styles.pairBtn}
        />
      </View>

      <FlatList
        data={nodes || []}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Claimed Nodes"
              description="Promote a host via `nexus node claim` or pair with a running node."
              icon={<Server size={40} color={colors.textMuted} />}
              action={
                <Button
                  title="Scan Pairing QR Code"
                  onPress={() => router.push('/nodes/pair')}
                />
              }
            />
          ) : undefined
        }
        renderItem={({ item }) => (
          <Card style={styles.card}>
            <View style={styles.nodeRow}>
              <View style={[styles.iconBox, { backgroundColor: colors.primarySubtle }]}>
                <Server size={20} color={colors.primary} />
              </View>
              <View style={styles.nodeInfo}>
                <Text style={[styles.nodeName, { color: colors.textPrimary }]}>{item.name}</Text>
                <Text style={[styles.nodePlatform, { color: colors.textMuted }]}>
                  Platform: {item.platform} · {item.is_active ? 'Active Server' : 'Standby'}
                </Text>
              </View>
              <StatusBadge status={item.is_active ? 'active' : 'offline'} />
            </View>

            <View style={[styles.divider, { backgroundColor: colors.surfaceBorder }]} />

            <View style={styles.endpointRow}>
              <Text style={[styles.endpointLabel, { color: colors.textMuted }]}>ENDPOINT</Text>
              <Text style={[styles.endpointValue, { color: colors.textSecondary }]} numberOfLines={1}>
                {item.endpoint || 'Encrypted Relay Bridge'}
              </Text>
            </View>
          </Card>
        )}
      />
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
  pairBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  list: {
    padding: 20,
    paddingTop: 4,
  },
  card: {
    marginBottom: 12,
  },
  nodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nodeInfo: {
    flex: 1,
  },
  nodeName: {
    fontSize: 16,
    fontWeight: '700',
  },
  nodePlatform: {
    fontSize: 12,
    marginTop: 2,
  },
  divider: {
    height: 1,
    marginVertical: 12,
  },
  endpointRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  endpointLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  endpointValue: {
    fontSize: 12,
    maxWidth: '75%',
  },
});
