import React from 'react';
import { Stack } from 'expo-router';
import { useTheme } from '../../../src/context/ThemeContext';

export default function NodesLayout() {
  const { colors } = useTheme();

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="pair" />
    </Stack>
  );
}
