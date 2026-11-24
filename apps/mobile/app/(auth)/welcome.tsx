import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Shield, Server, ArrowRight, CheckCircle2 } from 'lucide-react-native';
import { useTheme } from '../../src/context/ThemeContext';
import { useAuth } from '../../src/context/AuthContext';
import { Button } from '../../src/components/Button';
import { Input } from '../../src/components/Input';
import { Card } from '../../src/components/Card';
import { apiClient } from '../../src/api/client';
import { HealthCheckResponse } from '../../src/api/types';

export default function WelcomeScreen() {
  const { colors } = useTheme();
  const { serverUrl, updateServerUrl } = useAuth();
  const router = useRouter();

  const [customUrl, setCustomUrl] = useState(serverUrl);
  const [testingEndpoint, setTestingEndpoint] = useState(false);
  const [probeResult, setProbeResult] = useState<string | null>(null);

  const testServer = async () => {
    setTestingEndpoint(true);
    setProbeResult(null);
    try {
      await updateServerUrl(customUrl);
      const res = await apiClient<HealthCheckResponse>('/health');
      setProbeResult(`✓ Connected to ${res.service} (${res.mode})`);
    } catch (e: any) {
      setProbeResult(`✗ Connection failed: ${e.message}`);
    } finally {
      setTestingEndpoint(false);
    }
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <View style={[styles.emblem, { backgroundColor: colors.primarySubtle }]}>
            <Shield size={36} color={colors.primary} />
          </View>
          <Text style={[styles.brandTitle, { color: colors.textPrimary }]}>NEXUS</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Sovereign Personal Infrastructure & Mobile Companion
          </Text>
        </View>

        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <Server size={18} color={colors.primary} />
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>
              Control Plane Endpoint
            </Text>
          </View>
          <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
            Connect to the official hosted cloud control plane or your sovereign self-hosted Core node.
          </Text>

          <Input
            value={customUrl}
            onChangeText={setCustomUrl}
            placeholder="https://..."
            autoCapitalize="none"
            autoCorrect={false}
          />

          <View style={styles.row}>
            <Button
              title="Test Connection"
              variant="secondary"
              onPress={testServer}
              loading={testingEndpoint}
              style={{ flex: 1 }}
            />
          </View>

          {probeResult && (
            <Text
              style={[
                styles.probeText,
                { color: probeResult.startsWith('✓') ? colors.success : colors.danger },
              ]}
            >
              {probeResult}
            </Text>
          )}
        </Card>

        <View style={styles.highlights}>
          <View style={styles.featureRow}>
            <CheckCircle2 size={16} color={colors.primary} />
            <Text style={[styles.featureText, { color: colors.textSecondary }]}>
              Zero-Cloud Personal Storage: Data remains on your edge nodes
            </Text>
          </View>
          <View style={styles.featureRow}>
            <CheckCircle2 size={16} color={colors.primary} />
            <Text style={[styles.featureText, { color: colors.textSecondary }]}>
              Google OAuth Authentication with Hardware Keyring Isolation
            </Text>
          </View>
          <View style={styles.featureRow}>
            <CheckCircle2 size={16} color={colors.primary} />
            <Text style={[styles.featureText, { color: colors.textSecondary }]}>
              End-to-End Sealed Relays: ChaCha20-Poly1305 Tunnels
            </Text>
          </View>
        </View>

        <Button
          title="Continue to Sign In"
          onPress={() => router.push('/(auth)/sign-in')}
          icon={<ArrowRight size={18} color="#FFFFFF" />}
          style={styles.continueButton}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    padding: 24,
    justifyContent: 'center',
    flexGrow: 1,
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  emblem: {
    width: 68,
    height: 68,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  brandTitle: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  subtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginTop: 6,
    paddingHorizontal: 20,
    lineHeight: 20,
  },
  card: {
    marginBottom: 24,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    marginTop: 8,
  },
  probeText: {
    fontSize: 12,
    fontWeight: '600',
    marginTop: 10,
  },
  highlights: {
    marginBottom: 32,
    gap: 12,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  featureText: {
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
  continueButton: {
    marginTop: 'auto',
  },
});
