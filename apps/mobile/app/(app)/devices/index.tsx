import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, Alert, Platform, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Smartphone, Server, Plus, Trash2, QrCode } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Card } from '../../../src/components/Card';
import { Button } from '../../../src/components/Button';
import { StatusBadge } from '../../../src/components/StatusBadge';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { DeviceOut, NodeOut } from '../../../src/api/types';

export default function DevicesAndNodesScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeSegment, setActiveSegment] = useState<'devices' | 'nodes'>('devices');

  // Devices query & mutations
  const { data: devices, isLoading: devicesLoading, refetch: refetchDevices } = useQuery<DeviceOut[]>({
    queryKey: ['devices'],
    queryFn: () => apiClient<DeviceOut[]>('/api/devices'),
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      apiClient<DeviceOut>('/api/devices/register', {
        method: 'POST',
        body: JSON.stringify({
          name: `NEXUS ${Platform.OS === 'ios' ? 'iOS' : 'Android'} Companion`,
          platform: Platform.OS === 'ios' ? 'ios' : 'android',
          capabilities: ['mobile', 'camera', 'storage'],
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      Alert.alert('Device Registered', 'This mobile client is now registered with your sovereign account.');
    },
    onError: (err: any) => {
      Alert.alert('Registration Failed', err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      apiClient(`/api/devices/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
    onError: (err: any) => {
      Alert.alert('Revocation Failed', err.message);
    },
  });

  const confirmDelete = (device: DeviceOut) => {
    Alert.alert(
      'Revoke Device',
      `Are you sure you want to revoke "${device.name}"? It will no longer be able to synchronize or authenticate.`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Revoke', style: 'destructive', onPress: () => deleteMutation.mutate(device.id) },
      ]
    );
  };

  // Nodes query
  const { data: nodes, isLoading: nodesLoading, refetch: refetchNodes } = useQuery<NodeOut[]>({
    queryKey: ['nodes'],
    queryFn: () => apiClient<NodeOut[]>('/api/nodes'),
  });

  const isRefreshing = activeSegment === 'devices' ? devicesLoading : nodesLoading;
  const onRefresh = () => {
    if (activeSegment === 'devices') {
      refetchDevices();
    } else {
      refetchNodes();
    }
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      {/* Top Header */}
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Devices & Nodes</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            {activeSegment === 'devices'
              ? 'Authorized hardware clients and cryptographic endpoints'
              : 'Claimed sovereign servers and compute nodes'}
          </Text>
        </View>

        {activeSegment === 'devices' ? (
          <Button
            title="Register"
            icon={<Plus size={16} color="#FFFFFF" />}
            onPress={() => registerMutation.mutate()}
            loading={registerMutation.isPending}
            style={styles.actionBtn}
          />
        ) : (
          <Button
            title="Pair"
            icon={<QrCode size={16} color="#FFFFFF" />}
            onPress={() => router.push('/nodes/pair')}
            style={styles.actionBtn}
          />
        )}
      </View>

      {/* Segmented Switcher */}
      <View style={[styles.segmentContainer, { backgroundColor: colors.surfaceSubtle }]}>
        <TouchableOpacity
          style={[
            styles.segmentBtn,
            activeSegment === 'devices' && [styles.segmentBtnActive, { backgroundColor: colors.surface }],
          ]}
          onPress={() => setActiveSegment('devices')}
          activeOpacity={0.7}
        >
          <Smartphone size={16} color={activeSegment === 'devices' ? colors.primary : colors.textMuted} />
          <Text
            style={[
              styles.segmentText,
              { color: activeSegment === 'devices' ? colors.primary : colors.textSecondary },
            ]}
          >
            Connected Devices {devices ? `(${devices.length})` : ''}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.segmentBtn,
            activeSegment === 'nodes' && [styles.segmentBtnActive, { backgroundColor: colors.surface }],
          ]}
          onPress={() => setActiveSegment('nodes')}
          activeOpacity={0.7}
        >
          <Server size={16} color={activeSegment === 'nodes' ? colors.primary : colors.textMuted} />
          <Text
            style={[
              styles.segmentText,
              { color: activeSegment === 'nodes' ? colors.primary : colors.textSecondary },
            ]}
          >
            Edge Nodes {nodes ? `(${nodes.length})` : ''}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content: Devices Tab */}
      {activeSegment === 'devices' && (
        <FlatList
          data={devices || []}
          keyExtractor={(item) => String(item.id)}
          refreshing={isRefreshing}
          onRefresh={onRefresh}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !devicesLoading ? (
              <EmptyState
                title="No Registered Devices"
                description="Register this phone or connect desktop devices to view your sovereign fleet."
                icon={<Smartphone size={40} color={colors.textMuted} />}
                action={
                  <Button
                    title="Register This Mobile Device"
                    onPress={() => registerMutation.mutate()}
                    loading={registerMutation.isPending}
                  />
                }
              />
            ) : undefined
          }
          renderItem={({ item }) => (
            <Card style={styles.card}>
              <View style={styles.row}>
                <View style={[styles.iconBox, { backgroundColor: colors.primarySubtle }]}>
                  <Smartphone size={20} color={colors.primary} />
                </View>
                <View style={styles.info}>
                  <Text style={[styles.name, { color: colors.textPrimary }]}>{item.name}</Text>
                  <Text style={[styles.meta, { color: colors.textMuted }]}>
                    Platform: {item.platform} · ID: #{item.id}
                  </Text>
                </View>
                <StatusBadge status={item.is_online ? 'online' : 'offline'} />
              </View>

              <View style={[styles.cardDivider, { backgroundColor: colors.surfaceBorder }]} />

              <View style={styles.bottomRow}>
                <Text style={[styles.caps, { color: colors.textSecondary }]} numberOfLines={1}>
                  Caps: {item.capabilities || 'standard'}
                </Text>
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
      )}

      {/* Content: Nodes Tab */}
      {activeSegment === 'nodes' && (
        <FlatList
          data={nodes || []}
          keyExtractor={(item) => String(item.id)}
          refreshing={isRefreshing}
          onRefresh={onRefresh}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !nodesLoading ? (
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
              <View style={styles.row}>
                <View style={[styles.iconBox, { backgroundColor: colors.primarySubtle }]}>
                  <Server size={20} color={colors.primary} />
                </View>
                <View style={styles.info}>
                  <Text style={[styles.name, { color: colors.textPrimary }]}>{item.name}</Text>
                  <Text style={[styles.meta, { color: colors.textMuted }]}>
                    Platform: {item.platform} · {item.is_active ? 'Active Server' : 'Standby'}
                  </Text>
                </View>
                <StatusBadge status={item.is_active ? 'active' : 'offline'} />
              </View>

              <View style={[styles.cardDivider, { backgroundColor: colors.surfaceBorder }]} />

              <View style={styles.endpointRow}>
                <Text style={[styles.endpointLabel, { color: colors.textMuted }]}>ENDPOINT</Text>
                <Text style={[styles.endpointValue, { color: colors.textSecondary }]} numberOfLines={1}>
                  {item.endpoint || 'Encrypted Relay Bridge'}
                </Text>
              </View>
            </Card>
          )}
        />
      )}
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
    gap: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
  },
  subtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  actionBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  segmentContainer: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 12,
    borderRadius: 10,
    padding: 3,
    gap: 4,
  },
  segmentBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  segmentBtnActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  segmentText: {
    fontSize: 12,
    fontWeight: '700',
  },
  list: {
    padding: 20,
    paddingTop: 4,
  },
  card: {
    marginBottom: 12,
  },
  row: {
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
  info: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '700',
  },
  meta: {
    fontSize: 12,
    marginTop: 2,
  },
  cardDivider: {
    height: 1,
    marginVertical: 12,
  },
  bottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  caps: {
    fontSize: 12,
    flex: 1,
    marginRight: 12,
  },
  delBtn: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  endpointRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  endpointLabel: {
    fontSize: 11,
    fontWeight: '700',
  },
  endpointValue: {
    fontSize: 12,
    flex: 1,
    textAlign: 'right',
    marginLeft: 12,
  },
});
