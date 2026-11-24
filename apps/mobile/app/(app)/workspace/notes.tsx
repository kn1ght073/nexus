import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, FileText, Tag, Trash2 } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { EmptyState } from '../../../src/components/EmptyState';
import { apiClient } from '../../../src/api/client';
import { NoteOut } from '../../../src/api/types';

export default function NotesScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const { data: notes, isLoading, refetch } = useQuery<NoteOut[]>({
    queryKey: ['notes'],
    queryFn: () => apiClient<NoteOut[]>('/api/notes'),
  });

  const createNoteMutation = useMutation({
    mutationFn: () =>
      apiClient<NoteOut>('/api/notes', {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          content: content.trim(),
          tags: tags.trim() || undefined,
        }),
      }),
    onSuccess: () => {
      setTitle('');
      setContent('');
      setTags('');
      setShowAdd(false);
      queryClient.invalidateQueries({ queryKey: ['notes'] });
    },
    onError: (err: any) => {
      Alert.alert('Note Creation Failed', err.message);
    },
  });

  const deleteNoteMutation = useMutation({
    mutationFn: (id: number) => apiClient(`/api/notes/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes'] });
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
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Notes & Ideas</Text>
        <Button
          title=""
          icon={<Plus size={18} color="#FFFFFF" />}
          onPress={() => setShowAdd(!showAdd)}
          style={styles.addBtn}
        />
      </View>

      {showAdd && (
        <Card style={styles.createCard}>
          <Input
            value={title}
            onChangeText={setTitle}
            placeholder="Note title..."
          />
          <Input
            value={content}
            onChangeText={setContent}
            placeholder="Thoughts, meeting notes, code snippets..."
            multiline
            numberOfLines={4}
            style={{ height: 90 }}
          />
          <Input
            value={tags}
            onChangeText={setTags}
            placeholder="Tags (comma separated, e.g. research, kernel)"
            icon={<Tag size={16} color={colors.textMuted} />}
          />
          <Button
            title="Save Note"
            onPress={() => createNoteMutation.mutate()}
            loading={createNoteMutation.isPending}
            style={{ marginTop: 8 }}
          />
        </Card>
      )}

      <FlatList
        data={notes || []}
        keyExtractor={(item) => String(item.id)}
        refreshing={isLoading}
        onRefresh={refetch}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No Sovereign Notes"
              description="Capture encrypted thoughts and meeting minutes directly to your sovereign store."
              action={
                <Button
                  title="Capture Note"
                  onPress={() => setShowAdd(true)}
                />
              }
            />
          ) : undefined
        }
        renderItem={({ item }) => (
          <Card style={styles.noteCard}>
            <View style={styles.noteTop}>
              <Text style={[styles.noteTitle, { color: colors.textPrimary }]}>{item.title}</Text>
              <TouchableOpacity onPress={() => deleteNoteMutation.mutate(item.id)}>
                <Trash2 size={16} color={colors.textMuted} />
              </TouchableOpacity>
            </View>

            <Text style={[styles.noteBody, { color: colors.textSecondary }]} numberOfLines={3}>
              {item.content}
            </Text>

            {item.tags && (
              <View style={styles.tagRow}>
                {item.tags.split(',').map((t, idx) => (
                  <View key={idx} style={[styles.tagBadge, { backgroundColor: colors.surfaceSubtle }]}>
                    <Text style={[styles.tagText, { color: colors.primary }]}>#{t.trim()}</Text>
                  </View>
                ))}
              </View>
            )}
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
  addBtn: {
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
  createCard: {
    marginHorizontal: 20,
    marginBottom: 12,
  },
  list: {
    padding: 20,
    paddingTop: 4,
  },
  noteCard: {
    marginBottom: 10,
  },
  noteTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  noteTitle: {
    fontSize: 16,
    fontWeight: '700',
    flex: 1,
  },
  noteBody: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 10,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  tagBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  tagText: {
    fontSize: 11,
    fontWeight: '600',
  },
});
