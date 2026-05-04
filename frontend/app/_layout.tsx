import { normalizeAvatarValue } from '@/lib/avatar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import 'react-native-reanimated';
import { navigate, setRouter } from '../lib/navigation';

import { API_BASE } from '@/constants/env';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Platform } from 'react-native';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const theme = colorScheme === 'dark' ? 'dark' : 'light';
  const router = useRouter();

  useEffect(() => {
    console.log('[NLIP] API_BASE:', API_BASE);
  }, []);

  useEffect(() => {
    setRouter(router);
  }, [router]);

  // Refresh stored user info from server on app start
  useEffect(() => {
    // Install a global fetch wrapper that redirects to login on 401 responses.
    const originalFetch = global.fetch;
    (global as typeof global & { fetch: typeof fetch }).fetch = async (
      input: RequestInfo | URL,
      init?: RequestInit
    ) => {
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
            avatar_uri: normalizeAvatarValue(data.avatar_uri ?? null),
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
      try {
        (global as typeof global & { fetch: typeof fetch }).fetch = originalFetch;
      } catch {}
    };
  }, []);

  useEffect(() => {
    if (Platform.OS !== 'web' || typeof document === 'undefined') {
      return;
    }

    const backgroundColor = Colors[theme].background;
    const textColor = Colors[theme].text;
    document.documentElement.style.colorScheme = theme;
    document.documentElement.style.backgroundColor = backgroundColor;
    document.body.style.backgroundColor = backgroundColor;
    document.body.style.color = textColor;
  }, [theme]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack screenOptions={{ contentStyle: { backgroundColor: Colors[theme].background } }}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
      <StatusBar
        style={theme === 'dark' ? 'light' : 'dark'}
        backgroundColor={Colors[theme].background}
      />
    </ThemeProvider>
  );
}
