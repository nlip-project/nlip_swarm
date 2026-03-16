import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { API_BASE } from '@/constants/env';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { getContrastingTextColor } from '@/lib/color';
import { Stack, useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Alert, StyleSheet, TextInput, TouchableOpacity, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { fetchAndPersistUserProfile, persistUserLocally, StoredUser } from '@/lib/session';

export default function Signup() {
  const router = useRouter();
  const theme = useColorScheme();
  const colors = Colors[theme];
  const submitTextColor = getContrastingTextColor(colors.tint, colors.buttonText, colors.text);
  
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
        const baseUser: StoredUser = {
          user_id: data.user_id ?? null,
          session_id: data.session_id ?? null,
          name: data.name ?? name ?? null,
          email: data.email ?? email,
          location: data.location ?? location ?? null,
          phone_number: null,
          country_code: null,
          avatar_uri: null,
        };

        await persistUserLocally(baseUser);
        await fetchAndPersistUserProfile(baseUser);
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
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.icon, backgroundColor: colors.background },
        ]}
        placeholder="Full name"
        placeholderTextColor={colors.icon}
        selectionColor={colors.tint}
        cursorColor={colors.tint}
        keyboardAppearance={theme}
        autoCorrect={false}
        textContentType="name"
        value={name}
        onChangeText={setName}
      />
      <TextInput
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.icon, backgroundColor: colors.background },
        ]}
        placeholder="Email"
        placeholderTextColor={colors.icon}
        selectionColor={colors.tint}
        cursorColor={colors.tint}
        keyboardAppearance={theme}
        autoCapitalize="none"
        autoCorrect={false}
        spellCheck={false}
        autoComplete="email"
        textContentType="emailAddress"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.icon, backgroundColor: colors.background },
        ]}
        placeholder="Password"
        placeholderTextColor={colors.icon}
        selectionColor={colors.tint}
        cursorColor={colors.tint}
        keyboardAppearance={theme}
        autoCapitalize="none"
        autoCorrect={false}
        spellCheck={false}
        autoComplete="new-password"
        textContentType="newPassword"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      <TextInput
        style={[
          styles.input,
          { color: colors.text, borderColor: colors.icon, backgroundColor: colors.background },
        ]}
        placeholder="Location (optional)"
        placeholderTextColor={colors.icon}
        selectionColor={colors.tint}
        cursorColor={colors.tint}
        keyboardAppearance={theme}
        autoCorrect={false}
        textContentType="location"
        value={location}
        onChangeText={setLocation}
      />
      <TouchableOpacity
        style={[styles.submitButton, { backgroundColor: colors.tint, opacity: loading ? 0.7 : 1 }]}
        onPress={handleSignup}
        disabled={loading}
        accessibilityLabel="Sign up"
        activeOpacity={0.85}
      >
        <ThemedText style={[styles.submitButtonText, { color: submitTextColor }]}>
          {loading ? 'Signing up...' : 'Sign up'}
        </ThemedText>
      </TouchableOpacity>

        <View style={styles.row}>
          <ThemedText>Already have an account?</ThemedText>
          <TouchableOpacity onPress={() => router.push('/login')}>
            <ThemedText style={[styles.link, { color: colors.link }]}> Log in</ThemedText>
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
  submitButton: {
    marginTop: 4,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  submitButtonText: {
    fontSize: 16,
    lineHeight: 20,
    fontWeight: '600',
  },
  row: { flexDirection: 'row', justifyContent: 'center', marginTop: 12 },
  link: {},
});
