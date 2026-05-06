import Constants from 'expo-constants';
import { Platform } from 'react-native';

const rawApiBase = (process?.env?.EXPO_PUBLIC_API_BASE as string | undefined)?.trim();

function inferApiBaseFromExpoHost(): string | null {
	try {
		const hostUri =
			(Constants.expoConfig as any)?.hostUri ||
			(Constants.manifest2 as any)?.extra?.expoClient?.hostUri ||
			(Constants.manifest as any)?.debuggerHost;

		if (!hostUri || typeof hostUri !== 'string') return null;

		const host = hostUri.split(':')[0];
		if (!host) return null;

		return `http://${host}:8024`;
	} catch {
		return null;
	}
}

const inferredNativeApiBase = Platform.OS === 'web' ? null : inferApiBaseFromExpoHost();

export const API_BASE = rawApiBase || inferredNativeApiBase || 'http://localhost:8024';