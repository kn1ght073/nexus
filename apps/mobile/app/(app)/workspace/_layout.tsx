import React from 'react';
import { Stack } from 'expo-router';
import { useTheme } from '../../../src/context/ThemeContext';

export default function WorkspaceLayout() {
  const { colors } = useTheme();

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="tasks" />
      <Stack.Screen name="projects" />
      <Stack.Screen name="notes" />
      <Stack.Screen name="files" />
      <Stack.Screen name="sync" />
    </Stack>
  );
}
