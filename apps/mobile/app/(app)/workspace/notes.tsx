import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  TextInput,
  Modal,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Plus,
  FileText,
  Tag,
  Trash2,
  Search,
  FolderGit2,
  X,
  Edit3,
  Calendar,
} from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { NoteOut, ProjectOut } from '../../../src/api/types';
import {
  getLocalNotes,
  saveLocalNote,
  updateLocalNote,
  deleteLocalNote,
  cacheRemoteNotes,
  getLocalProjects,
} from '../../../src/api/workspaceStore';

export default function NotesScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  // Create form state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  // Filter & Search
  const [search, setSearch] = useState('');
  const [filterProjectId, setFilterProjectId] = useState<number | null>(null);

  // Note Viewer / Editor Modal
  const [viewingNote, setViewingNote] = useState<NoteOut | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editTags, setEditTags] = useState('');

  // Fetch Notes
  const { data: notes, isLoading, refetch } = useQuery<NoteOut[]>({
    queryKey: ['notes'],
    queryFn: async () => {
      try {
        const remote = await apiClient<NoteOut[]>('/api/notes');
        await cacheRemoteNotes(remote);
        return remote;
      } catch {
        return await getLocalNotes();
      }
    },
  });

  // Fetch Projects for association
  const { data: projects } = useQuery<ProjectOut[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      try {
        return await apiClient<ProjectOut[]>('/api/projects');
      } catch {
        return await getLocalProjects();
      }
    },
  });

  const projectMap = new Map<number, string>();
  (projects || []).forEach((p) => projectMap.set(p.id, p.title));

  // Create Note Mutation
  const createNoteMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        tags: tags.trim() || undefined,
        project_id: selectedProjectId,
      };
      try {
        return await apiClient<NoteOut>('/api/notes', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      } catch {
        return await saveLocalNote(payload);
      }
    },
    onSuccess: () => {
      setTitle('');
      setContent('');
      setTags('');
      setSelectedProjectId(null);
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['notes'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
    onError: (err: any) => {
      Alert.alert('Note Creation Failed', err.message);
    },
  });

  // Delete Note Mutation
  const deleteNoteMutation = useMutation({
    mutationFn: async (id: number) => {
      try {
        await apiClient(`/api/notes/${id}`, { method: 'DELETE' });
      } catch {
        // Fallback local deletion
      }
      await deleteLocalNote(id);
    },
    onSuccess: () => {
      if (viewingNote) setViewingNote(null);
      queryClient.invalidateQueries({ queryKey: ['notes'] });
      queryClient.invalidateQueries({ queryKey: ['accountOverview'] });
    },
  });

  // Update Note Mutation
  const handleSaveEdit = async () => {
    if (!viewingNote || !editTitle.trim()) return;
    const patch = {
      title: editTitle.trim(),
      content: editContent.trim(),
      tags: editTags.trim() || undefined,
    };
    try {
      await apiClient<NoteOut>(`/api/notes/${viewingNote.id}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      });
    } catch {
      await updateLocalNote(viewingNote.id, patch);
    }
    const updated = { ...viewingNote, ...patch, updated_at: new Date().toISOString() };
    setViewingNote(updated);
    setIsEditing(false);
    refetch();
    queryClient.invalidateQueries({ queryKey: ['notes'] });
  };

  const openViewModal = (note: NoteOut) => {
    setViewingNote(note);
    setEditTitle(note.title);
    setEditContent(note.content);
    setEditTags(note.tags || '');
    setIsEditing(false);
  };

  const filteredNotes = (notes || []).filter((n) => {
    const matchesProject = filterProjectId === null || n.project_id === filterProjectId;
    const matchesSearch =
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase()) ||
      (n.tags && n.tags.toLowerCase().includes(search.toLowerCase()));
    return matchesProject && matchesSearch;
  });

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      {/* Top Bar */}
      <View style={styles.topBar}>
        <Button
          title=""
          variant="outline"
          icon={<ArrowLeft size={20} color={colors.textPrimary} />}
          onPress={() => router.back()}
          style={styles.backBtn}
        />
        <View style={styles.titleContainer}>
          <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Notes & Ideas</Text>
          <Text style={[styles.topSubtitle, { color: colors.textMuted }]}>
            Sovereign Knowledge Vault & Markdown
          </Text>
        </View>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {/* Search & Project Filter */}
      <View style={styles.toolbar}>
        <View style={[styles.searchBox, { backgroundColor: colors.surface, borderColor: colors.surfaceBorder }]}>
          <Search size={14} color={colors.textMuted} />
          <TextInput
            placeholder="Search notes, tags, content..."
            placeholderTextColor={colors.textMuted}
            value={search}
            onChangeText={setSearch}
            style={[styles.searchInput, { color: colors.textPrimary }]}
          />
        </View>

        {projects && projects.length > 0 && (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterPillsRow}>
            <TouchableOpacity
              style={[
                styles.filterPill,
                filterProjectId === null && [styles.filterPillActive, { backgroundColor: colors.surface }],
                { borderColor: colors.surfaceBorder },
              ]}
              onPress={() => setFilterProjectId(null)}
            >
              <Text
                style={[
                  styles.filterPillText,
                  { color: filterProjectId === null ? colors.primary : colors.textSecondary },
                ]}
              >
                All Projects
              </Text>
            </TouchableOpacity>

            {projects.map((p) => {
              const active = filterProjectId === p.id;
              return (
                <TouchableOpacity
                  key={p.id}
                  style={[
                    styles.filterPill,
                    active && [styles.filterPillActive, { backgroundColor: colors.surface }],
                    { borderColor: colors.surfaceBorder },
                  ]}
                  onPress={() => setFilterProjectId(p.id)}
                >
                  <FolderGit2 size={12} color={active ? colors.accent : colors.textMuted} />
                  <Text
                    style={[
                      styles.filterPillText,
                      { color: active ? colors.accent : colors.textSecondary },
                    ]}
                  >
                    {p.title}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        )}
      </View>

      {/* Note Creation Card */}
      {showAdd && (
        <Card style={styles.createCard}>
          <Input
            value={title}
            onChangeText={setTitle}
            placeholder="Note title..."
            autoFocus
          />
          <Input
            value={content}
            onChangeText={setContent}
            placeholder="Capture thoughts, meetings, markdown, or snippets..."
            multiline
            numberOfLines={4}
            style={{ height: 84 }}
          />

          {/* Project Picker for New Note */}
          {projects && projects.length > 0 && (
            <View style={styles.projectPickerSection}>
              <Text style={[styles.pickerLabel, { color: colors.textMuted }]}>LINK TO PROJECT</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterPillsRow}>
                <TouchableOpacity
                  style={[
                    styles.filterPill,
                    selectedProjectId === null && [styles.filterPillActive, { backgroundColor: colors.primary }],
                    { borderColor: colors.surfaceBorder },
                  ]}
                  onPress={() => setSelectedProjectId(null)}
                >
                  <Text
                    style={[
                      styles.filterPillText,
                      { color: selectedProjectId === null ? '#FFF' : colors.textSecondary },
                    ]}
                  >
                    None
                  </Text>
                </TouchableOpacity>
                {projects.map((p) => {
                  const isSel = selectedProjectId === p.id;
                  return (
                    <TouchableOpacity
                      key={p.id}
                      style={[
                        styles.filterPill,
                        isSel && [styles.filterPillActive, { backgroundColor: colors.primary }],
                        { borderColor: colors.surfaceBorder },
                      ]}
                      onPress={() => setSelectedProjectId(p.id)}
                    >
                      <FolderGit2 size={12} color={isSel ? '#FFF' : colors.textMuted} />
                      <Text
                        style={[
                          styles.filterPillText,
                          { color: isSel ? '#FFF' : colors.textSecondary },
                        ]}
                      >
                        {p.title}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>
          )}

          <Input
            value={tags}
            onChangeText={setTags}
            placeholder="Tags (comma separated, e.g. research, ideas)"
            icon={<Tag size={14} color={colors.textMuted} />}
          />

          <Button
            title="Save Sovereign Note"
            onPress={() => createNoteMutation.mutate()}
            loading={createNoteMutation.isPending}
            style={{ marginTop: 8 }}
          />
        </Card>
      )}

      {/* Notes List */}
      <FlatList
        data={filteredNotes}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Notes Found"
              description="Capture quick ideas, technical notes, and sovereign knowledge that persist safely."
              icon={<FileText size={40} color={colors.textMuted} />}
              action={<Button title="Write New Note" onPress={() => setShowAdd(true)} />}
            />
          ) : undefined
        }
        renderItem={({ item }) => {
          const projectName = item.project_id ? projectMap.get(item.project_id) : null;
          const tagList = item.tags ? item.tags.split(',').map((t) => t.trim()).filter(Boolean) : [];

          return (
            <TouchableOpacity
              activeOpacity={0.8}
              onPress={() => openViewModal(item)}
            >
              <Card style={styles.noteCard}>
                <View style={styles.noteHeaderRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.noteTitle, { color: colors.textPrimary }]}>{item.title}</Text>
                    {projectName && (
                      <View style={[styles.projectTag, { backgroundColor: colors.accentSubtle }]}>
                        <FolderGit2 size={11} color={colors.accent} />
                        <Text style={[styles.projectTagText, { color: colors.accent }]} numberOfLines={1}>
                          {projectName}
                        </Text>
                      </View>
                    )}
                  </View>

                  <TouchableOpacity
                    style={styles.delBtn}
                    onPress={() => {
                      Alert.alert('Delete Note', `Delete "${item.title}"?`, [
                        { text: 'Cancel', style: 'cancel' },
                        { text: 'Delete', style: 'destructive', onPress: () => deleteNoteMutation.mutate(item.id) },
                      ]);
                    }}
                  >
                    <Trash2 size={16} color={colors.danger} />
                  </TouchableOpacity>
                </View>

                <Text style={[styles.noteContentPreview, { color: colors.textSecondary }]} numberOfLines={3}>
                  {item.content}
                </Text>

                {/* Footer with Tags & Date */}
                <View style={styles.noteFooter}>
                  <View style={styles.tagsContainer}>
                    {tagList.map((tag, idx) => (
                      <View key={idx} style={[styles.tagBadge, { backgroundColor: colors.surfaceSubtle }]}>
                        <Text style={[styles.tagText, { color: colors.textMuted }]}>#{tag}</Text>
                      </View>
                    ))}
                  </View>
                  <Text style={[styles.dateText, { color: colors.textMuted }]}>
                    {new Date(item.updated_at).toLocaleDateString()}
                  </Text>
                </View>
              </Card>
            </TouchableOpacity>
          );
        }}
      />

      {/* Note View & Edit Modal */}
      {viewingNote && (
        <Modal
          visible={Boolean(viewingNote)}
          animationType="slide"
          presentationStyle="pageSheet"
          onRequestClose={() => setViewingNote(null)}
        >
          <SafeAreaView style={[styles.modalContainer, { backgroundColor: colors.background }]}>
            {/* Modal Header */}
            <View style={styles.modalHeader}>
              <View style={{ flex: 1 }}>
                <Text style={[styles.modalHeaderTitle, { color: colors.textPrimary }]} numberOfLines={1}>
                  {isEditing ? 'Edit Note' : viewingNote.title}
                </Text>
                <Text style={[styles.modalHeaderSubtitle, { color: colors.textMuted }]}>
                  {new Date(viewingNote.updated_at).toLocaleString()}
                </Text>
              </View>

              <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                <Button
                  title=""
                  variant="outline"
                  icon={isEditing ? <FileText size={16} color={colors.textPrimary} /> : <Edit3 size={16} color={colors.primary} />}
                  onPress={() => setIsEditing(!isEditing)}
                  style={styles.headerIconBtn}
                />
                <Button
                  title=""
                  variant="outline"
                  icon={<Trash2 size={16} color={colors.danger} />}
                  onPress={() => {
                    Alert.alert('Delete Note', `Delete "${viewingNote.title}"?`, [
                      { text: 'Cancel', style: 'cancel' },
                      { text: 'Delete', style: 'destructive', onPress: () => deleteNoteMutation.mutate(viewingNote.id) },
                    ]);
                  }}
                  style={styles.headerIconBtn}
                />
                <TouchableOpacity
                  style={[styles.closeBtn, { backgroundColor: colors.surfaceSubtle }]}
                  onPress={() => setViewingNote(null)}
                >
                  <X size={18} color={colors.textPrimary} />
                </TouchableOpacity>
              </View>
            </View>

            <ScrollView contentContainerStyle={styles.modalBody}>
              {isEditing ? (
                <View style={styles.editSection}>
                  <Input
                    placeholder="Note title..."
                    value={editTitle}
                    onChangeText={setEditTitle}
                  />
                  <Input
                    placeholder="Note content..."
                    value={editContent}
                    onChangeText={setEditContent}
                    multiline
                    style={{ height: 200, textAlignVertical: 'top' }}
                  />
                  <Input
                    placeholder="Tags (comma separated)..."
                    value={editTags}
                    onChangeText={setEditTags}
                    icon={<Tag size={14} color={colors.textMuted} />}
                  />
                  <Button
                    title="Save Changes"
                    onPress={handleSaveEdit}
                    style={{ marginTop: 12 }}
                  />
                </View>
              ) : (
                <View>
                  {/* Linked Project Banner */}
                  {viewingNote.project_id && projectMap.has(viewingNote.project_id) && (
                    <View style={[styles.linkedProjectBanner, { backgroundColor: colors.accentSubtle }]}>
                      <FolderGit2 size={14} color={colors.accent} />
                      <Text style={[styles.linkedProjectText, { color: colors.accent }]}>
                        Part of {projectMap.get(viewingNote.project_id)}
                      </Text>
                    </View>
                  )}

                  <Text style={[styles.viewTitle, { color: colors.textPrimary }]}>
                    {viewingNote.title}
                  </Text>

                  <Card style={styles.viewContentCard}>
                    <Text style={[styles.viewContentText, { color: colors.textSecondary }]}>
                      {viewingNote.content}
                    </Text>
                  </Card>

                  {/* Tags */}
                  {viewingNote.tags ? (
                    <View style={styles.viewTagsRow}>
                      <Tag size={14} color={colors.textMuted} />
                      {viewingNote.tags.split(',').map((tag, i) => (
                        <View key={i} style={[styles.tagBadge, { backgroundColor: colors.surfaceSubtle }]}>
                          <Text style={[styles.tagText, { color: colors.primary }]}>#{tag.trim()}</Text>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              )}
            </ScrollView>
          </SafeAreaView>
        </Modal>
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
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  backBtn: {
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  titleContainer: {
    flex: 1,
  },
  topTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  topSubtitle: {
    fontSize: 12,
  },
  addBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  toolbar: {
    paddingHorizontal: 16,
    marginBottom: 8,
    gap: 8,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 10,
    height: 38,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 13,
    padding: 0,
  },
  filterPillsRow: {
    flexDirection: 'row',
    gap: 6,
    paddingVertical: 2,
  },
  filterPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
  },
  filterPillActive: {
    borderColor: 'transparent',
    elevation: 1,
  },
  filterPillText: {
    fontSize: 11,
    fontWeight: '600',
  },
  createCard: {
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 12,
  },
  projectPickerSection: {
    marginTop: 4,
    marginBottom: 6,
  },
  pickerLabel: {
    fontSize: 10,
    fontWeight: '700',
    marginBottom: 4,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  noteCard: {
    marginBottom: 10,
    padding: 14,
  },
  noteHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 8,
  },
  noteTitle: {
    fontSize: 16,
    fontWeight: '700',
    lineHeight: 22,
  },
  projectTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    alignSelf: 'flex-start',
    marginTop: 4,
  },
  projectTagText: {
    fontSize: 10,
    fontWeight: '700',
  },
  delBtn: {
    padding: 4,
  },
  noteContentPreview: {
    fontSize: 13,
    lineHeight: 18,
    marginTop: 8,
  },
  noteFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.05)',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    flex: 1,
  },
  tagBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  tagText: {
    fontSize: 10,
    fontWeight: '600',
  },
  dateText: {
    fontSize: 11,
    marginLeft: 8,
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  modalHeaderTitle: {
    fontSize: 17,
    fontWeight: '700',
  },
  modalHeaderSubtitle: {
    fontSize: 11,
    marginTop: 2,
  },
  headerIconBtn: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  closeBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalBody: {
    padding: 20,
  },
  editSection: {
    gap: 8,
  },
  linkedProjectBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginBottom: 12,
  },
  linkedProjectText: {
    fontSize: 12,
    fontWeight: '700',
  },
  viewTitle: {
    fontSize: 22,
    fontWeight: '800',
    marginBottom: 14,
    lineHeight: 28,
  },
  viewContentCard: {
    padding: 16,
    marginBottom: 16,
  },
  viewContentText: {
    fontSize: 15,
    lineHeight: 24,
  },
  viewTagsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
});
