import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE = (process?.env?.API_BASE as string) || 'http://0.0.0.0:8024';

export default function Signup() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
        body: JSON.stringify({ email, password, location }),
      });
      const data = await res.json();
      if (!res.ok) {
        Alert.alert('Signup failed', data?.detail || data?.message || 'Unknown error');
      } else {
        // Persist user info so other routes can gate on it
        const userObj = {
          user_id: data.user_id,
          session_id: data.session_id,
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
    <View style={styles.container}>
      <Text style={styles.title}>Sign Up</Text>
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
        <Text>Already have an account?</Text>
        <TouchableOpacity onPress={() => router.push('/login')}>
          <Text style={styles.link}> Log in</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: '600', marginBottom: 16, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 12, marginBottom: 12, borderRadius: 8 },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: 12 },
  link: { color: '#007AFF' },
});
