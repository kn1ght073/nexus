import React from 'react';
import { View, Text, StyleSheet, FlatList, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Smartphone, Plus, Trash2 } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Card } from '../../../src/components/Card';
import { Button } from '../../../src/components/Button';
import { StatusBadge } from '../../../src/components/StatusBadge';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { DeviceOut } from '../../../src/api/types';

export default function DevicesScreen() {
  const { colors } = useTheme();
  const queryClient = useQueryClient();

  const { data: devices, isLoading, refetch } = useQuery<DeviceOut[]>({
    queryKey: ['devices'],
    queryFn: () => apiClient<DeviceOut[]>('/api/devices'),
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      apiClient<DeviceOut>('/api/devices/register', {
        method: 'POST',
        body: JSON.stringify({
          name: 'NEXUS Mobile Companion',
          platform: 'mobile',
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

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Device Fleet</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Authorized hardware clients and cryptographic endpoints
          </Text>
        </View>
        <Button
          title="Register"
          icon={<Plus size={16} color="#FFFFFF" />}
          onPress={() => registerMutation.mutate()}
          loading={registerMutation.isPending}
          style={styles.regBtn}
        />
      </View>

      <FlatList
        data={devices || []}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
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
            <View style={styles.deviceRow}>
              <View style={[styles.iconBox, { backgroundColor: colors.primarySubtle }]}>
                <Smartphone size={20} color={colors.primary} />
              </View>
              <View style={styles.deviceInfo}>
                <Text style={[styles.deviceName, { color: colors.textPrimary }]}>{item.name}</Text>
                <Text style={[styles.deviceMeta, { color: colors.textMuted }]}>
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
  regBtn: {
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
  deviceRow: {
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
  deviceInfo: {
    flex: 1,
  },
  deviceName: {
    fontSize: 16,
    fontWeight: '700',
  },
  deviceMeta: {
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
});
