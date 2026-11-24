import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { ArrowLeft, QrCode, KeyRound, ShieldCheck } from 'lucide-react-native';
import { useTheme } from '../../../src/context/ThemeContext';
import { Button } from '../../../src/components/Button';
import { Input } from '../../../src/components/Input';
import { Card } from '../../../src/components/Card';
import { apiClient } from '../../../src/api/client';

export default function PairNodeScreen() {
  const { colors } = useTheme();
  const router = useRouter();

  const [numericCode, setNumericCode] = useState('');
  const [pairingLoading, setPairingLoading] = useState(false);

  const submitNumericCode = async () => {
    const code = numericCode.trim();
    if (!code || code.length < 6) {
      Alert.alert('Invalid Code', 'Please enter a valid 6-digit pairing code.');
      return;
    }

    setPairingLoading(true);
    try {
      const res = await apiClient<{ status: string; node_name?: string }>(
        '/api/pairing/exchange',
        {
          method: 'POST',
          body: JSON.stringify({
            code,
            device_name: 'NEXUS Mobile Companion',
          }),
        }
      );
      Alert.alert(
        'Pairing Successful',
        `Securely paired with node: ${res.node_name || 'Authorized Node'}.`,
        [{ text: 'OK', onPress: () => router.back() }]
      );
    } catch (err: any) {
      Alert.alert('Pairing Failed', err.message || 'The pairing code may have expired or is invalid.');
    } finally {
      setPairingLoading(false);
    }
  };

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
        <Text style={[styles.topTitle, { color: colors.textPrimary }]}>Pair Edge Node</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <KeyRound size={20} color={colors.primary} />
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>
              Enter 6-Digit Pairing Code
            </Text>
          </View>
          <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
            Run `nexus node pair` on your desktop node or server terminal to generate a short-lived pairing code.
          </Text>

          <Input
            value={numericCode}
            onChangeText={setNumericCode}
            placeholder="e.g. 849201"
            keyboardType="number-pad"
            maxLength={6}
            style={styles.codeInput}
          />

          <Button
            title="Complete Pairing"
            onPress={submitNumericCode}
            loading={pairingLoading}
            style={{ marginTop: 8 }}
          />
        </Card>

        <Card style={styles.card}>
          <View style={styles.cardHeader}>
            <QrCode size={20} color={colors.accent} />
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>
              Camera QR Code Scan
            </Text>
          </View>
          <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
            Scan the pairing QR code displayed in the Desktop Application or Web Console.
          </Text>

          <Button
            title="Open Camera Scanner"
            variant="secondary"
            onPress={() => {
              Alert.alert(
                'Camera Scanner',
                'Camera scanner active. In simulator/dev builds, use numeric code entry above.'
              );
            }}
          />
        </Card>

        <View style={styles.securityNote}>
          <ShieldCheck size={18} color={colors.success} />
          <Text style={[styles.securityText, { color: colors.textSecondary }]}>
            Pairing codes are cryptographically generated, single-use, and expire in 15 minutes.
          </Text>
        </View>
      </ScrollView>
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
    padding: 20,
  },
  card: {
    marginBottom: 16,
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
    marginBottom: 14,
  },
  codeInput: {
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: 4,
    textAlign: 'center',
  },
  securityNote: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 8,
    marginTop: 8,
  },
  securityText: {
    fontSize: 12,
    flex: 1,
    lineHeight: 16,
  },
});
