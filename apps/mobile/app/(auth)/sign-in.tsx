import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LogIn, Key, ArrowLeft } from 'lucide-react-native';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { useTheme } from '../../src/context/ThemeContext';
import { useAuth } from '../../src/context/AuthContext';
import { Button } from '../../src/components/Button';
import { Input } from '../../src/components/Input';
import { Card } from '../../src/components/Card';
import { apiClient } from '../../src/api/client';

WebBrowser.maybeCompleteAuthSession();

export default function SignInScreen() {
  const { colors } = useTheme();
  const { loginWithToken, serverUrl } = useAuth();
  const router = useRouter();

  const [manualToken, setManualToken] = useState('');
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [loadingManual, setLoadingManual] = useState(false);

  const startGoogleAuth = async () => {
    setLoadingGoogle(true);
    try {
      const redirectUri = Linking.createURL('auth/callback');
      const startRes = await apiClient<{ url?: string; auth_url?: string; state: string }>(
        '/api/auth/google/start',
        {
          method: 'POST',
          body: JSON.stringify({ redirect_uri: redirectUri }),
        }
      );

      const authTargetUrl = startRes.auth_url || startRes.url;
      if (!authTargetUrl) {
        throw new Error('Control plane returned empty Google authentication endpoint');
      }

      const result = await WebBrowser.openAuthSessionAsync(authTargetUrl, redirectUri);

      if (result.type === 'cancel' || result.type === 'dismiss') {
        // User closed the authentication window
        return;
      }

      if (result.type === 'success' && result.url) {
        const parsed = Linking.parse(result.url);
        const code = parsed.queryParams?.code as string;
        const state = parsed.queryParams?.state as string;

        if (code && state) {
          const tokenRes = await apiClient<{ access_token: string; refresh_token: string }>(
            '/api/auth/google/callback',
            {
              method: 'POST',
              body: JSON.stringify({ code, state }),
            }
          );
          await loginWithToken(tokenRes.access_token, tokenRes.refresh_token);
          router.replace('/(app)');
          return;
        }
      }
    } catch (err: any) {
      Alert.alert(
        'Google Authentication Notice',
        err.message || 'Google authentication could not be completed.'
      );
    } finally {
      setLoadingGoogle(false);
    }
  };

  const submitManualToken = async () => {
    if (!manualToken.trim()) {
      Alert.alert('Required', 'Please enter a valid session token.');
      return;
    }
    setLoadingManual(true);
    try {
      await loginWithToken(manualToken.trim());
      router.replace('/(app)');
    } catch (err: any) {
      Alert.alert('Login Failed', err.message || 'Invalid session token');
    } finally {
      setLoadingManual(false);
    }
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.topBar}>
        <Button
          title=""
          variant="outline"
          icon={<ArrowLeft size={20} color={colors.textPrimary} />}
          onPress={() => router.back()}
          style={styles.backBtn}
        />
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Sign In</Text>
        <View style={{ width: 44 }} />
      </View>

      <View style={styles.content}>
        <View style={styles.noticeBox}>
          <Text style={[styles.noticeTitle, { color: colors.textPrimary }]}>
            Sovereign Identity Access
          </Text>
          <Text style={[styles.noticeText, { color: colors.textSecondary }]}>
            NEXUS enforces strict Google OAuth admission. All identity claims are verified server-side against authorized node operators.
          </Text>
        </View>

        <Button
          title="Sign in with Google"
          onPress={startGoogleAuth}
          loading={loadingGoogle}
          icon={<LogIn size={18} color="#FFFFFF" />}
          style={styles.googleButton}
        />

        <View style={styles.dividerRow}>
          <View style={[styles.divider, { backgroundColor: colors.surfaceBorder }]} />
          <Text style={[styles.dividerText, { color: colors.textMuted }]}>
            OR SESSION TOKEN
          </Text>
          <View style={[styles.divider, { backgroundColor: colors.surfaceBorder }]} />
        </View>

        <Card>
          <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>
            Direct Session / Keyring Token
          </Text>
          <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
            Paste an active session token issued by your control plane or CLI (`nexus login`).
          </Text>

          <Input
            value={manualToken}
            onChangeText={setManualToken}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            secureTextEntry
            autoCapitalize="none"
            icon={<Key size={18} color={colors.textMuted} />}
          />

          <Button
            title="Authenticate with Token"
            variant="secondary"
            onPress={submitManualToken}
            loading={loadingManual}
            style={{ marginTop: 8 }}
          />
        </Card>
      </View>
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
  content: {
    padding: 24,
    flex: 1,
  },
  noticeBox: {
    marginBottom: 24,
  },
  noticeTitle: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 6,
  },
  noticeText: {
    fontSize: 14,
    lineHeight: 20,
  },
  googleButton: {
    marginBottom: 24,
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
    gap: 12,
  },
  divider: {
    flex: 1,
    height: 1,
  },
  dividerText: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 4,
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 12,
  },
});
