const rawApiBase = (process?.env?.EXPO_PUBLIC_API_BASE as string | undefined)?.trim();

export const API_BASE = rawApiBase || "http://localhost:8024";