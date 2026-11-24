import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../context/ThemeContext';

interface MetricBoxProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
}

export const MetricBox: React.FC<MetricBoxProps> = ({ label, value, subtext, icon }) => {
  const { colors } = useTheme();

  return (
    <View style={[styles.box, { backgroundColor: colors.surfaceSubtle, borderColor: colors.surfaceBorder }]}>
      <View style={styles.topRow}>
        <Text style={[styles.label, { color: colors.textMuted }]}>{label.toUpperCase()}</Text>
        {icon && <View>{icon}</View>}
      </View>
      <Text style={[styles.value, { color: colors.textPrimary }]}>{value}</Text>
      {subtext && <Text style={[styles.subtext, { color: colors.textSecondary }]}>{subtext}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  box: {
    flex: 1,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    marginHorizontal: 4,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  value: {
    fontSize: 22,
    fontWeight: '800',
  },
  subtext: {
    fontSize: 11,
    marginTop: 2,
  },
});
