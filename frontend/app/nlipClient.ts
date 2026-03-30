// Lightweight NLIP client for the frontend
// Provides sendMessage and attachment helpers that wrap request/response handling to the /nlip/ endpoint

import * as FileSystem from 'expo-file-system';
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

/** Custom error class for NLIP client failures with enhanced context */
export class NLIPError extends Error {
  constructor(
    public statusCode: number | null,
    public responseBody: string,
    public operation: string,
    message: string,
    public isRetryable: boolean = false
  ) {
    super(message);
    this.name = 'NLIPError';
  }

  toString(): string {
    const parts = [
      `[${this.operation}]`,
      this.statusCode ? `HTTP ${this.statusCode}` : 'Network Error',
      this.message,
    ];
    return parts.join(' ');
  }
}

export default class NLIPClient {
  baseUrl: string;
  timeout: number;
  correlator: string | null;
  private maxRetries: number = 2;
  private retryDelayMs: number = 500;

  constructor(baseUrl = '', options: { timeout?: number; maxRetries?: number } = {}) {
    // baseUrl should be origin like 'http://localhost:8000' (no trailing slash)
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeout = options.timeout ?? 30000;
    this.maxRetries = options.maxRetries ?? 2;
    this.correlator = null;
  }

  /** Determine if an error is retryable (transient) vs permanent */
  private isRetryableError(err: unknown): boolean {
    if (err instanceof NLIPError) {
      return err.isRetryable;
    }
    const msg = err instanceof Error ? err.message : String(err);
    // Retry on network timeouts, connection refusals, or server errors
    return (
      msg.includes('timeout') ||
      msg.includes('ECONNREFUSED') ||
      msg.includes('network') ||
      msg.includes('500') ||
      msg.includes('502') ||
      msg.includes('503') ||
      msg.includes('504')
    );
  }

  /** Exponential backoff for retry delay */
  private getRetryDelay(attempt: number): number {
    return this.retryDelayMs * Math.pow(2, attempt);
  }

  /** Send message with retry logic for transient failures */
  async sendMessage(request: NLIPRequest, attempt = 0): Promise<any> {
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
          throw new NLIPError(401, textBody, 'sendMessage', 'Unauthorized', false);
        }

        const isRetryable = res.status >= 500;
        const bodyPreview = textBody.slice(0, 200) || res.statusText;
        const msg = `HTTP ${res.status}: ${bodyPreview}`;
        throw new NLIPError(res.status, textBody, 'sendMessage', msg, isRetryable);
      }

      // Try to parse JSON; if parsing fails, return raw text
      if (!textBody) return null;
      try {
        return JSON.parse(textBody);
      } catch {
        console.warn('[NLIPClient] JSON parse failed, returning raw text');
        return textBody;
      }
    } catch (err) {
      const isRetryable = this.isRetryableError(err);
      
      // Wrap unknown errors in NLIPError for consistent handling
      if (!(err instanceof NLIPError)) {
        const msg = err instanceof Error ? err.message : String(err);
        const nlipErr = new NLIPError(null, '', 'sendMessage', msg, isRetryable);
        
        // Retry on transient errors
        if (isRetryable && attempt < this.maxRetries) {
          const delay = this.getRetryDelay(attempt);
          console.warn(
            `[NLIPClient] Transient error (attempt ${attempt + 1}/${this.maxRetries}), ` +
            `retrying in ${delay}ms: ${msg}`
          );
          await new Promise(resolve => setTimeout(resolve, delay));
          return this.sendMessage(request, attempt + 1);
        }
        
        throw nlipErr;
      }

      // Retry on transient NLIPError
      if (isRetryable && attempt < this.maxRetries) {
        const delay = this.getRetryDelay(attempt);
        console.warn(
          `[NLIPClient] Transient error (attempt ${attempt + 1}/${this.maxRetries}), ` +
          `retrying in ${delay}ms: ${err.message}`
        );
        await new Promise(resolve => setTimeout(resolve, delay));
        return this.sendMessage(request, attempt + 1);
      }

      // Give up after retries exhausted
      throw err;
    }
  }

  /** Read a local file URI and return base64 string (without data: prefix) */
  async uriToBase64(uri: string): Promise<string> {
    try {
      // expo-file-system readAsStringAsync returns base64 when encoding specified
      // Use string 'base64' for compatibility with different expo-file-system versions
      const result = await FileSystem.readAsStringAsync(uri, { encoding: 'base64' as any });
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      const nlipErr = new NLIPError(null, '', 'uriToBase64', `Failed to read file: ${msg}`, false);
      throw nlipErr;
    }
  }
}