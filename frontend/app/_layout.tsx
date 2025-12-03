import AsyncStorage from '@react-native-async-storage/async-storage';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import 'react-native-reanimated';
import { navigate, setRouter } from '../lib/navigation';

import { useColorScheme } from '@/hooks/use-color-scheme';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();
  // expose router to navigation helper
  setRouter(router);

  // Refresh stored user info from server on app start
  useEffect(() => {
    // Install a global fetch wrapper that redirects to login on 401 responses.
    const originalFetch = global.fetch;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (global as any).fetch = async (input: any, init?: any) => {
      try {
        const resp = await originalFetch(input, init);
        if (resp && resp.status === 401) {
          // clear stored user + chat state
          AsyncStorage.removeItem('user').catch(() => {});
          AsyncStorage.removeItem('current_conversation').catch(() => {});
          try { if (typeof window !== 'undefined' && window.localStorage) window.localStorage.removeItem('user'); } catch {}
          // redirect to login using central navigation helper
          try { navigate('/login'); } catch {}
        }
        return resp;
      } catch (e) {
        // If fetch itself fails, rethrow so callers can handle it
        throw e;
      }
    };

    let mounted = true;
    // const API_BASE = (process?.env?.API_BASE as string) || 'http://localhost:8024';
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
          try {
            await AsyncStorage.removeItem('user');
            await AsyncStorage.removeItem('current_conversation');
          } catch { /* ignore */ }
          try { if (typeof window !== 'undefined' && window.localStorage) window.localStorage.removeItem('user'); } catch { /* ignore */ }
        }
      } catch (e) {
        console.warn('Failed to refresh /me on startup', e);
      }
    })();
    return () => {
      mounted = false;
      // restore original fetch
      try { (global as any).fetch = originalFetch; } catch {}
    };
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
