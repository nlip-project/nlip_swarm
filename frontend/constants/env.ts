const rawApiBase = (process?.env?.EXPO_PUBLIC_API_BASE as string | undefined)?.trim();

if (!rawApiBase) {
	throw new Error(
		'EXPO_PUBLIC_API_BASE is not defined. Set it in your .env (e.g., EXPO_PUBLIC_API_BASE="http://localhost:8024").'
	);
}

export const API_BASE = rawApiBase;