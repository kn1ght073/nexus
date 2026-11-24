import React, { createContext, useContext, useState } from 'react';
import { useColorScheme } from 'react-native';
import { Colors, ThemeType } from '../theme/colors';

interface ThemeContextType {
  theme: ThemeType;
  colors: typeof Colors.dark;
  isDark: boolean;
  toggleTheme: () => void;
  setTheme: (t: ThemeType) => void;
}

const ThemeContext = createContext<ThemeContextType>({} as ThemeContextType);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const systemScheme = useColorScheme();
  const [theme, setTheme] = useState<ThemeType>(systemScheme === 'light' ? 'light' : 'dark');

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const colors = Colors[theme];
  const isDark = theme === 'dark';

  return (
    <ThemeContext.Provider value={{ theme, colors, isDark, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
