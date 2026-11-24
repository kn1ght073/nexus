import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Folder, File, ChevronRight } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { FileItem, StorageRootsResponse } from '../../../src/api/types';

export default function FilesScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  const [currentPath, setCurrentPath] = useState<string>('');

  const { data: roots } = useQuery<StorageRootsResponse>({
    queryKey: ['storageRoots'],
    queryFn: () => apiClient<StorageRootsResponse>('/api/files/roots'),
  });

  const { data: files, isLoading, refetch } = useQuery<FileItem[]>({
    queryKey: ['files', currentPath],
    queryFn: () => apiClient<FileItem[]>(`/api/files/browse?path=${encodeURIComponent(currentPath)}`),
  });

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.topBar}>
        <Button
          title=""
          variant="outline"
          icon={<ArrowLeft size={20} color={colors.textPrimary} />}
          onPress={() => {
            if (currentPath) {
              const parts = currentPath.split('/').filter(Boolean);
              parts.pop();
              setCurrentPath(parts.join('/'));
            } else {
              router.back();
            }
          }}
          style={styles.backBtn}
        />
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Storage Roots</Text>
        <View style={{ width: 44 }} />
      </View>

      <View style={[styles.pathBar, { backgroundColor: colors.surfaceSubtle }]}>
        <Folder size={14} color={colors.primary} />
        <Text style={[styles.pathText, { color: colors.textSecondary }]} numberOfLines={1}>
          /{currentPath || 'roots'}
        </Text>
      </View>

      <FlatList
        data={files || []}
        keyExtractor={(item) => item.path}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="Storage Directory Empty"
              description="No files or subdirectories found within this sandboxed storage root."
              icon={<Folder size={40} color={colors.textMuted} />}
            />
          ) : undefined
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            activeOpacity={0.7}
            disabled={!item.is_dir}
            onPress={() => {
              if (item.is_dir) {
                setCurrentPath(item.path);
              }
            }}
          >
            <Card style={styles.fileCard}>
              <View style={styles.fileRow}>
                {item.is_dir ? (
                  <Folder size={20} color={colors.primary} />
                ) : (
                  <File size={20} color={colors.textMuted} />
                )}
                <View style={styles.fileInfo}>
                  <Text style={[styles.fileName, { color: colors.textPrimary }]}>{item.name}</Text>
                  <Text style={[styles.fileSize, { color: colors.textMuted }]}>
                    {item.is_dir ? 'Directory' : `${(item.size / 1024).toFixed(1)} KB`}
                  </Text>
                </View>
                {item.is_dir && <ChevronRight size={16} color={colors.textMuted} />}
              </View>
            </Card>
          </TouchableOpacity>
        )}
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
  topTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  pathBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginHorizontal: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginBottom: 8,
  },
  pathText: {
    fontSize: 12,
    fontWeight: '600',
  },
  list: {
    padding: 20,
    paddingTop: 4,
  },
  fileCard: {
    marginVertical: 4,
    paddingVertical: 12,
  },
  fileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 14,
    fontWeight: '600',
  },
  fileSize: {
    fontSize: 11,
    marginTop: 2,
  },
});
