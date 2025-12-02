// Lightweight NLIP client for the frontend
// Provides sendMessage and attachment helpers that wrap request/response handling to the /nlip/ endpoint

import * as FileSystem from 'expo-file-system';
import { Linking } from 'react-native';
import { navigate } from '../lib/navigation';

type NLIPSubmessage = {
  format: string;
  subformat?: string;
  content?: any;
  label?: string;
};

export type NLIPRequest = {
  format: string;
  subformat?: string;
  content?: any;
  submessages?: NLIPSubmessage[];
  metadata?: any;
};

export default class NLIPClient {
  baseUrl: string;
  timeout: number;
  correlator: string | null;

  constructor(baseUrl = '', options: { timeout?: number } = {}) {
    // baseUrl should be origin like 'http://localhost:8000' (no trailing slash)
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = options.timeout ?? 30000;
    this.correlator = null;
  }

  async sendMessage(request: NLIPRequest): Promise<any> {
    try {
      const res = await fetch(`${this.baseUrl}/nlip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      // Read the response body as text first so we can include it in errors
      const textBody = await res.text().catch(() => '');

      if (!res.ok) {
        // If unauthorized, send the user to the login page immediately.
        if (res.status === 401) {
          try { navigate('/login'); } catch {}
        }

        // Include response body (if any) to aid debugging; fallback to statusText
        const bodyPreview = textBody ? textBody : res.statusText;
        throw new Error(`HTTP ${res.status}: ${bodyPreview}`);
      }

      // Try to parse JSON; if parsing fails, return raw text
      if (!textBody) return null;
      try {
        return JSON.parse(textBody);
      } catch {
        return textBody;
      }
    } catch (err) {
      // Re-throw with any additional context preserved
      throw err;
    }
  }

  // Read a local file URI and return base64 string (without data: prefix)
  async uriToBase64(uri: string) {
    // expo-file-system readAsStringAsync returns base64 when encoding specified
    // Use string 'base64' for compatibility with different expo-file-system versions
    const result = await FileSystem.readAsStringAsync(uri, { encoding: 'base64' as any });
    return result;
  }
}