import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { API_BASE } from '@/constants/env';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Stack, useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Alert, Button, StyleSheet, TextInput, TouchableOpacity, View } from 'react-native';
import { fetchAndPersistUserProfile, persistUserLocally, StoredUser } from '@/lib/session';

export default function Login() {
  const router = useRouter();
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
        // Always clear conversation selection when switching accounts so chat UI starts fresh
        try {
          await AsyncStorage.removeItem('current_conversation');
        } catch (e) {
          console.warn('Failed to clear current conversation before login', e);
        }
        // Persist minimal user info locally so we can gate routes
        const baseUser: StoredUser = {
          user_id: data.user_id ?? null,
          session_id: data.session_id ?? null,
          name: data.name ?? null,
          email: data.email ?? email,
          location: data.location ?? null,
          phone_number: null,
          country_code: null,
          avatar_uri: null,
        };

        await persistUserLocally(baseUser);
        await fetchAndPersistUserProfile(baseUser);
        try { router.replace('/'); } catch { /* ignore */ }
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
          <ThemedText>Don&apos;t have an account?</ThemedText>
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
