import * as FileSystem from 'expo-file-system';

const BASE64_VALUE_REGEX = /^[A-Za-z0-9+/=\s]+$/;

export function inferMimeTypeFromUri(uri: string | null) {
  if (!uri) return 'image/jpeg';
  const lower = uri.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.gif')) return 'image/gif';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.heic') || lower.endsWith('.heif')) return 'image/heic';
  return 'image/jpeg';
}

export function normalizeAvatarValue(raw: string | null) {
  if (!raw) return null;
  if (/^data:/i.test(raw) || /^https?:\/\//i.test(raw) || /^file:/i.test(raw)) {
    return raw;
  }
  if (BASE64_VALUE_REGEX.test(raw) && raw.length > 100) {
    return `data:image/jpeg;base64,${raw}`;
  }
  return raw;
}

export async function encodeUriToDataUri(uri: string) {
  const mime = inferMimeTypeFromUri(uri);
  const base64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  return `data:${mime};base64,${base64}`;
}
