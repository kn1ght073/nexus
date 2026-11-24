export const Colors = {
  dark: {
    background: '#090D16',
    surface: '#0F172A',
    surfaceSubtle: '#1E293B',
    surfaceBorder: '#334155',
    textPrimary: '#F8FAFC',
    textSecondary: '#94A3B8',
    textMuted: '#64748B',
    primary: '#0EA5E9',       // Electric Cyan
    primaryHover: '#38BDF8',
    primarySubtle: 'rgba(14, 165, 233, 0.15)',
    accent: '#6366F1',        // Indigo
    accentSubtle: 'rgba(99, 102, 241, 0.15)',
    success: '#10B981',       // Emerald
    successSubtle: 'rgba(16, 185, 129, 0.15)',
    warning: '#F59E0B',       // Amber
    warningSubtle: 'rgba(245, 158, 11, 0.15)',
    danger: '#EF4444',        // Rose
    dangerSubtle: 'rgba(239, 68, 68, 0.15)',
    card: '#0F172A',
    cardBorder: 'rgba(51, 65, 85, 0.8)',
  },
  light: {
    background: '#F8FAFC',
    surface: '#FFFFFF',
    surfaceSubtle: '#F1F5F9',
    surfaceBorder: '#E2E8F0',
    textPrimary: '#0F172A',
    textSecondary: '#475569',
    textMuted: '#94A3B8',
    primary: '#0284C7',
    primaryHover: '#0369A1',
    primarySubtle: 'rgba(2, 132, 199, 0.1)',
    accent: '#4F46E5',
    accentSubtle: 'rgba(79, 70, 229, 0.1)',
    success: '#059669',
    successSubtle: 'rgba(5, 150, 105, 0.1)',
    warning: '#D97706',
    warningSubtle: 'rgba(217, 119, 6, 0.1)',
    danger: '#DC2626',
    dangerSubtle: 'rgba(220, 38, 38, 0.1)',
    card: '#FFFFFF',
    cardBorder: '#E2E8F0',
  }
};

export type ThemeType = 'dark' | 'light';
