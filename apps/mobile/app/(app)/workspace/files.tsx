import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Folder,
  File,
  ChevronRight,
  HardDrive,
  FolderTree,
  Lock,
  FileCode,
  FileText,
  FileArchive,
  Image,
  FolderCheck,
} from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { FileItem } from '../../../src/api/types';

// Mock structure for showcase/offline/control-plane storage roots
const SHOWCASE_ROOTS: { name: string; path: string; description: string; iconType: string }[] = [
  {
    name: 'Sovereign Documents',
    path: 'documents',
    description: 'Personal records, contracts, identity keys & specs',
    iconType: 'docs',
  },
  {
    name: 'Research & Vault',
    path: 'vault',
    description: 'Encrypted notes, API archives & credentials',
    iconType: 'vault',
  },
  {
    name: 'Projects & Codebases',
    path: 'projects',
    description: 'Local git checkouts, build artifacts & scripts',
    iconType: 'code',
  },
  {
    name: 'Backups & Snapshots',
    path: 'backups',
    description: 'System state snapshots & node sync archives',
    iconType: 'archive',
  },
];

const SHOWCASE_SUBDIRECTORIES: Record<string, FileItem[]> = {
  'documents': [
    { name: 'Identity & Certificates', path: 'documents/certs', is_dir: true, size: 4096, modified_at: new Date().toISOString() },
    { name: 'Sovereign Architecture Spec.pdf', path: 'documents/Sovereign_Spec.pdf', is_dir: false, size: 245000, modified_at: new Date().toISOString() },
    { name: 'Node Hardware Inventory.json', path: 'documents/Node_Inventory.json', is_dir: false, size: 1420, modified_at: new Date().toISOString() },
  ],
  'documents/certs': [
    { name: 'nexus-root-ca.crt', path: 'documents/certs/nexus-root-ca.crt', is_dir: false, size: 1820, modified_at: new Date().toISOString() },
    { name: 'device-identity-key.pub', path: 'documents/certs/device-identity-key.pub', is_dir: false, size: 420, modified_at: new Date().toISOString() },
  ],
  'vault': [
    { name: 'Encrypted Backups', path: 'vault/backups', is_dir: true, size: 4096, modified_at: new Date().toISOString() },
    { name: 'secrets.env.enc', path: 'vault/secrets.env.enc', is_dir: false, size: 3420, modified_at: new Date().toISOString() },
    { name: 'recovery-phrases.txt.gpg', path: 'vault/recovery-phrases.txt.gpg', is_dir: false, size: 890, modified_at: new Date().toISOString() },
  ],
  'vault/backups': [
    { name: '2026-11-snapshot.tar.zst', path: 'vault/backups/2026-11-snapshot.tar.zst', is_dir: false, size: 125000000, modified_at: new Date().toISOString() },
  ],
  'projects': [
    { name: 'nexus-core-daemon', path: 'projects/nexus-core-daemon', is_dir: true, size: 4096, modified_at: new Date().toISOString() },
    { name: 'mobile-companion', path: 'projects/mobile-companion', is_dir: true, size: 4096, modified_at: new Date().toISOString() },
    { name: 'system-agent', path: 'projects/system-agent', is_dir: true, size: 4096, modified_at: new Date().toISOString() },
  ],
  'projects/nexus-core-daemon': [
    { name: 'main.py', path: 'projects/nexus-core-daemon/main.py', is_dir: false, size: 6800, modified_at: new Date().toISOString() },
    { name: 'settings.py', path: 'projects/nexus-core-daemon/settings.py', is_dir: false, size: 3400, modified_at: new Date().toISOString() },
  ],
  'projects/mobile-companion': [
    { name: 'app.config.ts', path: 'projects/mobile-companion/app.config.ts', is_dir: false, size: 1800, modified_at: new Date().toISOString() },
    { name: 'package.json', path: 'projects/mobile-companion/package.json', is_dir: false, size: 1240, modified_at: new Date().toISOString() },
  ],
  'projects/system-agent': [
    { name: 'agent.rs', path: 'projects/system-agent/agent.rs', is_dir: false, size: 8900, modified_at: new Date().toISOString() },
    { name: 'Cargo.toml', path: 'projects/system-agent/Cargo.toml', is_dir: false, size: 560, modified_at: new Date().toISOString() },
  ],
  'backups': [
    { name: 'daily-sqlite-dump.sql.gz', path: 'backups/daily-sqlite-dump.sql.gz', is_dir: false, size: 840000, modified_at: new Date().toISOString() },
    { name: 'wireguard-config-archive.zip', path: 'backups/wireguard-config-archive.zip', is_dir: false, size: 32000, modified_at: new Date().toISOString() },
  ],
};

export default function FilesScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  const [currentPath, setCurrentPath] = useState<string>('');

  // Fetch real storage roots if an edge node is responding
  const { data: serverRoots, isError: rootsError } = useQuery<string[]>({
    queryKey: ['storageRoots'],
    queryFn: async () => {
      try {
        const res = await apiClient<any>('/api/files/roots');
        if (Array.isArray(res)) return res;
        if (res && Array.isArray(res.roots)) return res.roots;
        return [];
      } catch {
        return [];
      }
    },
    retry: 1,
  });

  // Query directory contents if currentPath is set
  const { data: serverFiles, isLoading, refetch } = useQuery<FileItem[]>({
    queryKey: ['files', currentPath],
    queryFn: async () => {
      if (!currentPath) return [];
      try {
        return await apiClient<FileItem[]>(`/api/files/browse?path=${encodeURIComponent(currentPath)}`);
      } catch {
        // Fall back to showcase files for seamless offline navigation
        return SHOWCASE_SUBDIRECTORIES[currentPath] || [];
      }
    },
    enabled: Boolean(currentPath),
  });

  const pathParts = currentPath.split('/').filter(Boolean);

  const getFileIcon = (item: FileItem) => {
    if (item.is_dir) {
      return <Folder size={22} color={colors.primary} />;
    }
    const ext = item.name.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
      case 'py':
      case 'ts':
      case 'rs':
        return <FileCode size={22} color={colors.accent} />;
      case 'pdf':
      case 'txt':
      case 'md':
        return <FileText size={22} color={colors.success} />;
      case 'zip':
      case 'tar':
      case 'gz':
      case 'zst':
        return <FileArchive size={22} color={colors.warning} />;
      case 'png':
      case 'jpg':
      case 'svg':
        return <Image size={22} color={colors.textSecondary} />;
      default:
        return <File size={22} color={colors.textMuted} />;
    }
  };

  const getRootIcon = (iconType: string) => {
    switch (iconType) {
      case 'vault':
        return <Lock size={22} color={colors.accent} />;
      case 'code':
        return <FileCode size={22} color={colors.primary} />;
      case 'archive':
        return <FileArchive size={22} color={colors.warning} />;
      default:
        return <HardDrive size={22} color={colors.success} />;
    }
  };

  const activeFiles = currentPath ? (serverFiles || SHOWCASE_SUBDIRECTORIES[currentPath] || []) : [];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      {/* Top Header */}
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
        <View style={styles.titleContainer}>
          <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Storage Roots</Text>
          <Text style={[styles.topSubtitle, { color: colors.textMuted }]}>
            {currentPath ? 'Jailed Directory Viewer' : 'Sovereign Root Mounts'}
          </Text>
        </View>
        <View style={{ width: 44 }} />
      </View>

      {/* Breadcrumbs Navigation */}
      <View style={[styles.breadcrumbContainer, { backgroundColor: colors.surfaceSubtle }]}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.breadcrumbContent}>
          <TouchableOpacity
            style={styles.breadcrumbItem}
            onPress={() => setCurrentPath('')}
          >
            <FolderTree size={14} color={currentPath === '' ? colors.primary : colors.textMuted} />
            <Text
              style={[
                styles.breadcrumbText,
                { color: currentPath === '' ? colors.primary : colors.textSecondary, fontWeight: currentPath === '' ? '700' : '500' },
              ]}
            >
              Roots
            </Text>
          </TouchableOpacity>

          {pathParts.map((part, index) => {
            const subPath = pathParts.slice(0, index + 1).join('/');
            const isLast = index === pathParts.length - 1;
            return (
              <React.Fragment key={subPath}>
                <ChevronRight size={12} color={colors.textMuted} />
                <TouchableOpacity
                  style={styles.breadcrumbItem}
                  onPress={() => setCurrentPath(subPath)}
                  disabled={isLast}
                >
                  <Text
                    style={[
                      styles.breadcrumbText,
                      { color: isLast ? colors.primary : colors.textSecondary, fontWeight: isLast ? '700' : '500' },
                    ]}
                  >
                    {part}
                  </Text>
                </TouchableOpacity>
              </React.Fragment>
            );
          })}
        </ScrollView>
      </View>

      {/* Main Content: Roots Showcase OR Directory View */}
      {!currentPath ? (
        <ScrollView contentContainerStyle={styles.list}>
          <View style={styles.sectionHeader}>
            <FolderCheck size={16} color={colors.primary} />
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
              Mounted Sovereign Directories
            </Text>
          </View>

          {/* If server returned actual roots, render them */}
          {serverRoots && serverRoots.length > 0 ? (
            serverRoots.map((root, idx) => (
              <TouchableOpacity
                key={idx}
                activeOpacity={0.7}
                onPress={() => setCurrentPath(root)}
              >
                <Card style={styles.rootCard}>
                  <View style={styles.rootRow}>
                    <View style={[styles.iconBox, { backgroundColor: colors.surfaceSubtle }]}>
                      <HardDrive size={22} color={colors.primary} />
                    </View>
                    <View style={styles.rootInfo}>
                      <Text style={[styles.rootName, { color: colors.textPrimary }]}>
                        {root.split('/').filter(Boolean).pop() || root}
                      </Text>
                      <Text style={[styles.rootDesc, { color: colors.textMuted }]} numberOfLines={1}>
                        {root}
                      </Text>
                    </View>
                    <ChevronRight size={18} color={colors.textMuted} />
                  </View>
                </Card>
              </TouchableOpacity>
            ))
          ) : (
            // Showcase Sub-folder Showcase
            SHOWCASE_ROOTS.map((root, idx) => (
              <TouchableOpacity
                key={idx}
                activeOpacity={0.7}
                onPress={() => setCurrentPath(root.path)}
              >
                <Card style={styles.rootCard}>
                  <View style={styles.rootRow}>
                    <View style={[styles.iconBox, { backgroundColor: colors.surfaceSubtle }]}>
                      {getRootIcon(root.iconType)}
                    </View>
                    <View style={styles.rootInfo}>
                      <View style={styles.rootTitleRow}>
                        <Text style={[styles.rootName, { color: colors.textPrimary }]}>{root.name}</Text>
                        <View style={[styles.pathPill, { backgroundColor: colors.surfaceSubtle }]}>
                          <Text style={[styles.pathPillText, { color: colors.textMuted }]}>
                            /{root.path}
                          </Text>
                        </View>
                      </View>
                      <Text style={[styles.rootDesc, { color: colors.textSecondary }]}>
                        {root.description}
                      </Text>
                    </View>
                    <ChevronRight size={18} color={colors.textMuted} />
                  </View>
                </Card>
              </TouchableOpacity>
            ))
          )}
        </ScrollView>
      ) : (
        <FlatList
          data={activeFiles}
          keyExtractor={(item) => item.path}
          refreshing={isLoading}
          onRefresh={refetch}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !isLoading ? (
              <EmptyState
                title="Storage Directory Empty"
                description="No files or subdirectories found within this storage root."
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
                  <View style={[styles.fileIconBox, { backgroundColor: colors.surfaceSubtle }]}>
                    {getFileIcon(item)}
                  </View>
                  <View style={styles.fileInfo}>
                    <Text style={[styles.fileName, { color: colors.textPrimary }]}>{item.name}</Text>
                    <Text style={[styles.fileSize, { color: colors.textMuted }]}>
                      {item.is_dir
                        ? 'Directory Folder'
                        : `${(item.size / 1024).toFixed(1)} KB`}
                    </Text>
                  </View>
                  {item.is_dir && <ChevronRight size={16} color={colors.textMuted} />}
                </View>
              </Card>
            </TouchableOpacity>
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
  titleContainer: {
    alignItems: 'center',
  },
  topTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  topSubtitle: {
    fontSize: 11,
    fontWeight: '500',
    marginTop: 1,
  },
  breadcrumbContainer: {
    marginHorizontal: 20,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
    marginBottom: 8,
  },
  breadcrumbContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  breadcrumbItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  breadcrumbText: {
    fontSize: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
    marginTop: 4,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
  },
  list: {
    padding: 20,
    paddingTop: 4,
    gap: 8,
  },
  rootCard: {
    marginVertical: 4,
    paddingVertical: 14,
  },
  rootRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rootInfo: {
    flex: 1,
  },
  rootTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  rootName: {
    fontSize: 15,
    fontWeight: '700',
  },
  pathPill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  pathPillText: {
    fontSize: 10,
    fontFamily: 'monospace',
  },
  rootDesc: {
    fontSize: 12,
    lineHeight: 16,
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
  fileIconBox: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 14,
    fontWeight: '600',
  },
  fileSize: {
    fontSize: 12,
    marginTop: 2,
  },
});
