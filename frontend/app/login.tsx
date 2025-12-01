import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Alert, TouchableOpacity } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';

const API_BASE = (process?.env?.API_BASE as string) || 'http://0.0.0.0:8024';

export default function Login() {
  const router = useRouter();
  const theme = useColorScheme() ?? 'light';
  const c = Colors[theme];
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!email || !password) {
      Alert.alert('Missing fields', 'Please enter email and password');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        Alert.alert('Login failed', data?.detail || data?.message || 'Unknown error');
      } else {
        // Persist minimal user info locally so we can gate routes
        const userObj = {
          user_id: data.user_id,
          session_id: data.session_id,
          name: data.name ?? null,
          email: data.email ?? email,
          location: data.location ?? null,
        };
        try {
          await AsyncStorage.setItem('user', JSON.stringify(userObj));
        } catch (e) {
          console.warn('Failed to persist user data (AsyncStorage)', e);
        }
        // Also write to window.localStorage for web clients
        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('user', JSON.stringify(userObj));
          }
        } catch (e) {
          // ignore
        }
        Alert.alert('Logged in', `Welcome ${data.email ?? ''}`);
        try { router.replace('/profile'); } catch { /* ignore */ }
      }
    } catch (err) {
      console.error(err);
      Alert.alert('Network error', String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <ThemedView style={styles.container}>
        <ThemedText style={styles.title}>Login</ThemedText>
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      <Button title={loading ? 'Logging in...' : 'Login'} onPress={handleLogin} disabled={loading} />

        <View style={styles.row}>
          <ThemedText>Don't have an account?</ThemedText>
          <TouchableOpacity onPress={() => router.push('/signup')}>
            <ThemedText style={styles.link}> Sign up</ThemedText>
          </TouchableOpacity>
        </View>
      </ThemedView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: '600', marginBottom: 16, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 12, marginBottom: 12, borderRadius: 8 },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: 12 },
  link: { color: '#007AFF' },
});
