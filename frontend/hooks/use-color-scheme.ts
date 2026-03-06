import { Appearance, useColorScheme as useRNColorScheme } from 'react-native';

export function useColorScheme(): 'light' | 'dark' {
  return useRNColorScheme() ?? Appearance.getColorScheme() ?? 'light';
}
