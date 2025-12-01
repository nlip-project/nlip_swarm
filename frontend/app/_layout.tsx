import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import React, { useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useColorScheme } from '@/hooks/use-color-scheme';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // Refresh stored user info from server on app start
  useEffect(() => {
    let mounted = true;
    const API_BASE = (process?.env?.API_BASE as string) || 'http://0.0.0.0:8024';
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/me`, { method: 'GET', credentials: 'include' });
        if (!mounted) return;
        if (res.ok) {
          const data = await res.json();
          const userObj = {
            user_id: data.user_id,
            name: data.name ?? null,
            email: data.email ?? null,
            location: data.location ?? null,
            phone_number: data.phone_number ?? null,
            country_code: data.country_code ?? null,
            avatar_uri: data.avatar_uri ?? null,
            session_id: null,
          };
          try { await AsyncStorage.setItem('user', JSON.stringify(userObj)); } catch { /* ignore */ }
          try { if (typeof window !== 'undefined' && window.localStorage) window.localStorage.setItem('user', JSON.stringify(userObj)); } catch { /* ignore */ }
        } else if (res.status === 401) {
          // Not authenticated — clear stored user
          try { await AsyncStorage.removeItem('user'); } catch { /* ignore */ }
          try { if (typeof window !== 'undefined' && window.localStorage) window.localStorage.removeItem('user'); } catch { /* ignore */ }
        }
      } catch (e) {
        console.warn('Failed to refresh /me on startup', e);
      }
    })();
    return () => { mounted = false; };
  }, []);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
