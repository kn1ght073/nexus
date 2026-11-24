import React, { useEffect } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../../src/context/ThemeContext';
import { useAuth } from '../../src/context/AuthContext';
import { apiClient } from '../../src/api/client';

export default function AuthCallback() {
  const { code, state } = useLocalSearchParams<{ code?: string; state?: string }>();
  const { colors } = useTheme();
  const { loginWithToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      if (code && state) {
        try {
          const res = await apiClient<{ access_token: string; refresh_token: string }>(
            '/api/auth/google/callback',
            {
              method: 'POST',
              body: JSON.stringify({ code, state }),
            }
          );
          await loginWithToken(res.access_token, res.refresh_token);
          router.replace('/(app)');
        } catch (e) {
          router.replace('/(auth)/sign-in');
        }
      } else {
        router.replace('/(auth)/sign-in');
      }
    })();
  }, [code, state, loginWithToken, router]);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <ActivityIndicator size="large" color={colors.primary} />
      <Text style={[styles.text, { color: colors.textSecondary }]}>
        Completing Sovereign Authentication...
      </Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  text: {
    fontSize: 14,
    fontWeight: '600',
  },
});
