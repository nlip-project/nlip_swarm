import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { AvatarPicker } from '@/components/profile/AvatarPicker';
import { PhoneField } from '@/components/profile/PhoneField';
import { ProfileActions } from '@/components/profile/ProfileActions';
import { ProfileTextField } from '@/components/profile/TextField';
import { ThemedView } from '@/components/themed-view';
import { API_BASE } from '@/constants/env';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useImageAttachment } from '@/hooks/use-image-attachment';
import { encodeUriToDataUri, normalizeAvatarValue } from '@/lib/avatar';
import { persistUserLocally, StoredUser } from '@/lib/session';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';

export default function ProfileScreen() {
  const router = useRouter();
  const theme = (useColorScheme() ?? 'light') as 'light' | 'dark';
  const c = Colors[theme];
  const insets = useSafeAreaInsets();
  const headerOffset = Math.min(Math.max(insets.top + 8, 12), 48);
  const bottomInset = insets.bottom + 32;

  const [name, setName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [email, setEmail] = useState('');
  const [location, setLocation] = useState('');
  const [avatarPreviewUri, setAvatarPreviewUri] = useState<string | null>(null);
  const [avatarUploadDataUri, setAvatarUploadDataUri] = useState<string | null>(null);
  const [isProcessingPhoto, setIsProcessingPhoto] = useState(false);

  const prepareAvatarUpload = useCallback(async (uri: string) => {
    setAvatarPreviewUri(uri);
    setIsProcessingPhoto(true);
    try {
      const dataUri = await encodeUriToDataUri(uri);
      setAvatarPreviewUri(dataUri);
      setAvatarUploadDataUri(dataUri);
    } catch (error) {
      console.warn('Failed to encode avatar', error);
      Alert.alert('Error', 'Failed to process the selected image. Please try again.');
    } finally {
      setIsProcessingPhoto(false);
    }
  }, []);

  const { openCamera, pickImageFromLibrary } = useImageAttachment({
    onImageSelected: (uri) => {
      void prepareAvatarUpload(uri);
    },
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
          if (u?.avatar_uri) setAvatarPreviewUri(normalizeAvatarValue(u.avatar_uri));
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
    if (isProcessingPhoto) {
      Alert.alert('Please wait', 'Still processing the selected photo. Try again in a moment.');
      return;
    }
    const phoneDigits = phoneNumber ? phoneNumber.replace(/\D/g, '') : '';
    const payload = {
      name: name || undefined,
      location: location || undefined,
      phone_number: phoneDigits || undefined,
      country_code: countryCode || undefined,
      avatar_uri: avatarUploadDataUri || undefined,
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

      const userObj: StoredUser = {
        user_id: data.user_id ?? (existing?.user_id ?? null),
        session_id: existing?.session_id ?? null,
        name: data.name ?? name ?? null,
        email: data.email ?? email ?? null,
        location: data.location ?? location ?? null,
        phone_number: data.phone_number ? formatPhoneNumber(String(data.phone_number).replace(/\D/g, '')) : (phoneNumber ?? null),
        country_code: data.country_code ?? (countryCode || null),
        avatar_uri: normalizeAvatarValue(data.avatar_uri ?? existing?.avatar_uri ?? avatarPreviewUri ?? null),
      };

      setAvatarPreviewUri(userObj.avatar_uri);
      setAvatarUploadDataUri(null);

      await persistUserLocally(userObj);

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
              <AvatarPicker
                uri={avatarPreviewUri}
                name={name}
                colors={c}
                onPress={handleChangePhoto}
                isProcessing={isProcessingPhoto}
              />

              <View style={styles.form}>
                <ProfileTextField
                  label="Name"
                  value={name}
                  onChangeText={setName}
                  placeholder="Name"
                  autoCapitalize="words"
                  returnKeyType="next"
                  colors={c}
                  theme={theme}
                />

                <PhoneField
                  colors={c}
                  theme={theme}
                  countryCode={countryCode}
                  phoneNumber={phoneNumber}
                  onCountryCodeChange={handleCountryCodeChange}
                  onPhoneNumberChange={(text) => {
                    const digits = text.replace(/\D/g, '').slice(0, 10);
                    setPhoneNumber(formatPhoneNumber(digits));
                  }}
                />

                <ProfileTextField
                  label="Email"
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@example.com"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  returnKeyType="next"
                  colors={c}
                  theme={theme}
                />

                <ProfileTextField
                  label="Location"
                  value={location}
                  onChangeText={setLocation}
                  placeholder="City, Country"
                  returnKeyType="done"
                  colors={c}
                  theme={theme}
                />

                <ProfileActions
                  onSave={handleSave}
                  onLogout={handleLogout}
                  tintColor={c.tint}
                  disabled={isProcessingPhoto}
                />
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
  form: {
    gap: 12,
  },
});
