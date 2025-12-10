import AsyncStorage from '@react-native-async-storage/async-storage';

import { API_BASE } from '@/constants/env';
import { normalizeAvatarValue } from './avatar';

export type StoredUser = {
  user_id: string | null;
  session_id: string | null;
  name: string | null;
  email: string | null;
  location: string | null;
  phone_number: string | null;
  country_code: string | null;
  avatar_uri: string | null;
};

const defaultStoredUser: StoredUser = {
  user_id: null,
  session_id: null,
  name: null,
  email: null,
  location: null,
  phone_number: null,
  country_code: null,
  avatar_uri: null,
};

export async function persistUserLocally(user: StoredUser) {
  try {
    await AsyncStorage.setItem('user', JSON.stringify(user));
  } catch (e) {
    console.warn('Failed to persist user (AsyncStorage)', e);
  }

  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('user', JSON.stringify(user));
    }
  } catch (e) {
    console.warn('Failed to persist user (window.localStorage)', e);
  }
}

export async function fetchAndPersistUserProfile(overrides: Partial<StoredUser> = {}) {
  try {
    const res = await fetch(`${API_BASE}/me`, { method: 'GET', credentials: 'include' });
    if (!res.ok) {
      return null;
    }
    const data = await res.json();

    const user: StoredUser = {
      ...defaultStoredUser,
      user_id: data.user_id ?? overrides.user_id ?? null,
      session_id: overrides.session_id ?? null,
      name: data.name ?? overrides.name ?? null,
      email: data.email ?? overrides.email ?? null,
      location: data.location ?? overrides.location ?? null,
      phone_number: data.phone_number ?? overrides.phone_number ?? null,
      country_code: data.country_code ?? overrides.country_code ?? null,
      avatar_uri: normalizeAvatarValue(data.avatar_uri ?? overrides.avatar_uri ?? null),
    };

    await persistUserLocally(user);
    return user;
  } catch (e) {
    console.warn('Failed to refresh /me profile', e);
    return null;
  }
}
