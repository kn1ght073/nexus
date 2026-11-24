import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../context/ThemeContext';

interface StatusBadgeProps {
  status: 'online' | 'offline' | 'active' | 'pending' | 'completed' | 'warning' | string;
  label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const { colors } = useTheme();

  const getStyle = () => {
    switch (status.toLowerCase()) {
      case 'online':
      case 'active':
      case 'completed':
        return {
          bg: colors.successSubtle,
          text: colors.success,
          dot: colors.success,
        };
      case 'pending':
      case 'warning':
        return {
          bg: colors.warningSubtle,
          text: colors.warning,
          dot: colors.warning,
        };
      case 'offline':
      case 'cancelled':
      case 'error':
        return {
          bg: colors.dangerSubtle,
          text: colors.danger,
          dot: colors.danger,
        };
      default:
        return {
          bg: colors.surfaceSubtle,
          text: colors.textSecondary,
          dot: colors.textMuted,
        };
    }
  };

  const style = getStyle();

  return (
    <View style={[styles.badge, { backgroundColor: style.bg }]}>
      <View style={[styles.dot, { backgroundColor: style.dot }]} />
      <Text style={[styles.label, { color: style.text }]}>
        {label || status.toUpperCase()}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    gap: 6,
    alignSelf: 'flex-start',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  label: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
