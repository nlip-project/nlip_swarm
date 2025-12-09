import React, { useEffect, useState } from 'react';
import {
  Alert,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useImageAttachment } from '@/hooks/use-image-attachment';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';

export default function ProfileScreen() {
  const router = useRouter();
  const theme = useColorScheme() ?? 'light';
  const c = Colors[theme];
  const API_BASE = (process?.env?.API_BASE as string) || 'http://0.0.0.0:8024';
  const insets = useSafeAreaInsets();
  const headerOffset = Math.min(Math.max(insets.top + 8, 12), 48);
  const bottomInset = insets.bottom + 32;

  const [name, setName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [email, setEmail] = useState('');
  const [location, setLocation] = useState('');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);
  const { openCamera, pickImageFromLibrary } = useImageAttachment({
    onImageSelected: setAvatarUri,
    cameraOptions: {
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
      permissionMessage: 'Camera permission is required to take a profile photo.',
    },
    libraryOptions: {
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
      allowsMultipleSelection: false,
      permissionMessage: 'Photo library permission is required to choose a profile photo.',
    },
  });

  function handleCountryCodeChange(text: string) {
    // Only allow digits
    const cleaned = text.replace(/\D/g, '');
    setCountryCode(cleaned);
  }

  function formatPhoneNumber(digits: string) {
    if (!digits) return '';
    const d = String(digits).replace(/\D/g, '').slice(0, 10);
    const p1 = d.slice(0, 3);
    const p2 = d.slice(3, 6);
    const p3 = d.slice(6, 10);
    if (d.length <= 3) return `(${p1}`;
    if (d.length <= 6) return `(${p1}) ${p2}`;
    return `(${p1}) ${p2}-${p3}`;
  }

  // Load user data from storage (AsyncStorage or window.localStorage) on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        let raw = null;
        try {
          raw = await AsyncStorage.getItem('user');
        } catch {
          // ignore
        }
        if (!raw && typeof window !== 'undefined' && window.localStorage) {
          try {
            raw = window.localStorage.getItem('user');
          } catch {
            // ignore
          }
        }
        if (mounted && raw) {
          const u = JSON.parse(raw);
          if (u?.email) setEmail(u.email);
          if (u?.location) setLocation(u.location);
          if (u?.name) setName(u.name);
          if (u?.phone_number) setPhoneNumber(formatPhoneNumber(String(u.phone_number).replace(/\D/g, '')));
          if (u?.country_code) setCountryCode(u.country_code);
          if (u?.avatar_uri) setAvatarUri(u.avatar_uri);
        }
      } catch (e) {
        console.warn('Failed to load user for profile', e);
      }
    })();
    return () => { mounted = false; };
  }, []);

  function handleChangePhoto() {
    Keyboard.dismiss();
    Alert.alert('Profile Photo', 'Choose an option', [
      { text: 'Take Photo', onPress: () => void openCamera() },
      { text: 'Choose from Library', onPress: () => void pickImageFromLibrary() },
      { text: 'Cancel', style: 'cancel' },
    ]);
  }

  async function handleSave() {
    Keyboard.dismiss();
    const phoneDigits = phoneNumber ? phoneNumber.replace(/\D/g, '') : '';
    const payload = {
      name: name || undefined,
      location: location || undefined,
      phone_number: phoneDigits || undefined,
      country_code: countryCode || undefined,
      avatar_uri: avatarUri || undefined,
    };

    try {
      const res = await fetch(`${API_BASE}/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        Alert.alert('Save failed', data?.detail || data?.message || 'Unknown error');
        return;
      }

      // Merge with existing stored session_id if present
      let existingRaw = null;
      try { existingRaw = await AsyncStorage.getItem('user'); } catch { existingRaw = null; }
      let existing = null;
      if (!existingRaw && typeof window !== 'undefined' && window.localStorage) {
        try { existingRaw = window.localStorage.getItem('user'); } catch { existingRaw = null; }
      }
      if (existingRaw) {
        try { existing = JSON.parse(existingRaw); } catch { existing = null; }
      }

      const userObj: any = {
        user_id: data.user_id ?? (existing?.user_id ?? null),
        session_id: existing?.session_id ?? null,
        name: data.name ?? name ?? null,
        email: data.email ?? email ?? null,
        location: data.location ?? location ?? null,
        phone_number: data.phone_number ? formatPhoneNumber(String(data.phone_number).replace(/\D/g, '')) : (phoneNumber ?? null),
        country_code: data.country_code ?? (countryCode || null),
        avatar_uri: data.avatar_uri ?? avatarUri ?? null,
      };

      try { await AsyncStorage.setItem('user', JSON.stringify(userObj)); } catch (e) { console.warn('Failed to persist user (AsyncStorage)', e); }
      try { if (typeof window !== 'undefined' && window.localStorage) window.localStorage.setItem('user', JSON.stringify(userObj)); } catch { /* ignore */ }

      Alert.alert('Saved', 'Profile updated');
    } catch (err) {
      console.error('Failed to save profile', err);
      Alert.alert('Network error', String(err));
    }
  }

  async function handleLogout() {
    Keyboard.dismiss();
    Alert.alert('Log out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log out',
        style: 'destructive',
        onPress: async () => {
          // First try to notify the backend to invalidate the session / clear cookie
          try {
            await fetch(`${API_BASE}/logout`, {
              method: 'POST',
              credentials: 'include',
            });
          } catch (e) {
            // network error — proceed to clear client state anyway
            console.warn('Logout request failed', e);
          }

          // Clear all client-side persisted state so next login starts clean
          try {
            await AsyncStorage.clear();
          } catch (err) {
            console.warn('Failed to clear AsyncStorage on logout', err);
          }
          try {
            if (typeof window !== 'undefined' && window.localStorage) {
              window.localStorage.clear();
            }
          } catch (err) {
            console.warn('Failed to clear window.localStorage on logout', err);
          }

          // Navigate to login
          try {
            router.replace('/login');
          } catch {
            console.warn('Navigation error on logout');
          }
        },
      },
    ]);
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex1}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
    >
      <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
        <SafeAreaView style={[styles.flex1, { backgroundColor: c.background }]} edges={["top", "bottom"]}>
          <ThemedView style={styles.container}>
            <ScrollView
              contentContainerStyle={[
                styles.scrollContent,
                { paddingBottom: bottomInset, paddingTop: headerOffset },
              ]}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              <View style={styles.header}>
                <TouchableOpacity style={[styles.avatar, { borderColor: c.icon }]} onPress={handleChangePhoto} accessibilityLabel="Change profile photo">
                  {avatarUri ? (
                    <Image source={{ uri: avatarUri }} style={styles.avatarImage} />
                  ) : (() => {
                    const initials = name
                      .split(' ')
                      .map(part => part.charAt(0))
                      .filter(Boolean)
                      .join('')
                      .toUpperCase();
                    return initials ? (
                      <ThemedText style={[styles.avatarInitials]}>{initials}</ThemedText>
                    ) : (
                      <Ionicons name="person" size={56} color={c.icon} />
                    );
                  })()}
                </TouchableOpacity>
                <TouchableOpacity onPress={handleChangePhoto}>
                  <ThemedText type="link">Change Photo</ThemedText>
                </TouchableOpacity>
              </View>

              <View style={styles.form}>
                <View style={styles.fieldGroup}>
                <ThemedText>Name</ThemedText>
                <TextInput
                  value={name}
                  onChangeText={setName}
                  placeholder="Name"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Phone Number</ThemedText>
                <View style={styles.phoneRow}>
                  <View style={[styles.countryCodeInput, { borderColor: c.icon, backgroundColor: c.background }]}>
                    <ThemedText style={styles.plusSign}>+</ThemedText>
                    <TextInput
                      value={countryCode}
                      onChangeText={handleCountryCodeChange}
                      placeholder="1"
                      placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                      style={[styles.codeInput, { color: c.text }]}
                      keyboardType="number-pad"
                      maxLength={3}
                      returnKeyType="next"
                    />
                  </View>
                  <TextInput
                    value={phoneNumber}
                    onChangeText={(text) => {
                      const digits = text.replace(/\D/g, '').slice(0, 10);
                      setPhoneNumber(formatPhoneNumber(digits));
                    }}
                    placeholder="(123) 456-7890"
                    placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                    style={[styles.input, styles.phoneInput, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                    keyboardType="phone-pad"
                    maxLength={14}
                  />
                </View>
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Email</ThemedText>
                <TextInput
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@example.com"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  keyboardType="email-address"
                  returnKeyType="next"
                />
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Location</ThemedText>
                <TextInput
                  value={location}
                  onChangeText={setLocation}
                  placeholder="City, Country"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  returnKeyType="done"
                />
              </View>
                <View style={styles.actionsContainer}>
                  <TouchableOpacity onPress={handleSave} style={[styles.primaryButton, { backgroundColor: c.tint }]} accessibilityLabel="Save profile">
                    <ThemedText style={styles.primaryButtonText}>Save</ThemedText>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={handleLogout} style={styles.destructiveButton} accessibilityLabel="Log out">
                    <ThemedText style={styles.destructiveButtonText}>Log out</ThemedText>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </ThemedView>
        </SafeAreaView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  container: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 0,
    gap: 24,
    justifyContent: 'flex-start',
  },
  scrollContent: {
    flexGrow: 1,
    gap: 20,
  },
  header: {
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 120,
    height: 120,
    borderRadius: 60,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  avatarImage: {
    width: '100%',
    height: '100%',
  },
  avatarInitials: {
    fontSize: 36,
    lineHeight: 42,
    textAlign: 'center',
  },
  form: {
    gap: 12,
  },
  fieldGroup: {
    gap: 6,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  phoneRow: {
    flexDirection: 'row',
    gap: 8,
  },
  countryCodeInput: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    minWidth: 70,
  },
  plusSign: {
    fontSize: 16,
    marginRight: 2,
  },
  codeInput: {
    fontSize: 16,
    minWidth: 30,
    padding: 0,
  },
  phoneInput: {
    flex: 1,
  },
  actionsContainer: {
    marginTop: 8,
    alignItems: 'center',
    width: '100%',
    gap: 8,
  },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 12,
    minWidth: 160,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  destructiveButton: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    width: 160,
  },
  destructiveButtonText: {
    color: '#d9534f',
    fontWeight: '600',
  },
});
