import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Alert, TouchableOpacity } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';

// const API_BASE = (process?.env?.API_BASE as string) || 'http://localhost:8024';
const API_BASE = (process?.env?.API_BASE as string) || 'http://0.0.0.0:8024';

export default function Signup() {
  const router = useRouter();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSignup() {
    if (!email || !password) {
      Alert.alert('Missing fields', 'Please enter email and password');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name, email, password, location }),
      });
      const data = await res.json();
      if (!res.ok) {
        Alert.alert('Signup failed', data?.detail || data?.message || 'Unknown error');
      } else {
        // Clear any lingering chat selection before storing the new account locally
        try {
          await AsyncStorage.removeItem('current_conversation');
        } catch (e) {
          console.warn('Failed to clear current conversation before signup login', e);
        }
        // Persist user info so other routes can gate on it
        const userObj = {
          user_id: data.user_id,
          session_id: data.session_id,
          name: data.name ?? name ?? null,
          email: data.email ?? email,
          location: data.location ?? location ?? null,
        };
        try {
          await AsyncStorage.setItem('user', JSON.stringify(userObj));
        } catch (e) {
          console.warn('Failed to persist user data (AsyncStorage)', e);
        }
        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            window.localStorage.setItem('user', JSON.stringify(userObj));
          }
        } catch (e) {
          // ignore
        }
        Alert.alert('Signed up', `Account created for ${data.email || email}`);
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
        <ThemedText style={styles.title}>Sign Up</ThemedText>
      <TextInput
        style={styles.input}
        placeholder="Full name"
        value={name}
        onChangeText={setName}
      />
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
      <TextInput
        style={styles.input}
        placeholder="Location (optional)"
        value={location}
        onChangeText={setLocation}
      />
      <Button title={loading ? 'Signing up...' : 'Sign up'} onPress={handleSignup} disabled={loading} />

        <View style={styles.row}>
          <ThemedText>Already have an account?</ThemedText>
          <TouchableOpacity onPress={() => router.push('/login')}>
            <ThemedText style={styles.link}> Log in</ThemedText>
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
