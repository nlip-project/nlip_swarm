// Lightweight NLIP client for the frontend
// Provides sendMessage and attachment helpers that wrap request/response handling to the /nlip/ endpoint

import * as FileSystem from 'expo-file-system';

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

  async sendMessage(text: string) {
    const payload: any = {
      format: 'text',
      subformat: 'plain',
      content: text,
      submessages: [
        {
          format: 'generic',
          subformat: 'translation_request',
          content: { target_language: 'en' },
        },
      ],
    };

    if (this.correlator) {
      // add conversation token as a submessage if we have one
      payload.submessages.push({ format: 'token', subformat: 'conversation', content: this.correlator });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(`${this.baseUrl}/nlip/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        const textBody = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${textBody || res.statusText}`);
      }

      const data = await res.json();

      // if the response contains a conversation token, capture it
      if (Array.isArray(data?.submessages)) {
        const conv = data.submessages.find((s: any) => s?.format?.toLowerCase?.() === 'token' && s?.subformat?.toLowerCase?.().startsWith('conversation'));
        if (conv?.content) this.correlator = conv.content;
      }

      // prefer top-level content string
      if (typeof data?.content === 'string' && data.content.trim().length > 0) return data.content;

      // fallback: first text submessage
      if (Array.isArray(data?.submessages)) {
        const firstText = data.submessages.find((s: any) => s?.format?.toLowerCase?.() === 'text' && typeof s?.content === 'string');
        if (firstText?.content) return firstText.content;
      }

      // final fallback
      return typeof data === 'object' ? JSON.stringify(data) : String(data);
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err?.name === 'AbortError') {
        throw new Error('Request timed out');
      }
      throw err;
    }
  }

  // Read a local file URI and return base64 string (without data: prefix)
  private async uriToBase64(uri: string) {
    // expo-file-system readAsStringAsync returns base64 when encoding specified
    // Use string 'base64' for compatibility with different expo-file-system versions
    const result = await FileSystem.readAsStringAsync(uri, { encoding: 'base64' as any });
    return result;
  }

  // Send text with an image attachment (local file URI). Returns reply string.
  async sendWithImage(text: string, uri: string, filename?: string, mimeType?: string) {
    const base64 = await this.uriToBase64(uri);
    // determine extension or encoding from mimeType or filename
    let ext = 'bin';
    if (mimeType) {
      const parts = mimeType.split('/');
      ext = parts[1] || parts[0];
    } else if (filename) {
      const parts = filename.split('.');
      ext = parts.length > 1 ? parts.pop() as string : 'bin';
    }

    const payload: any = {
      format: 'text',
      subformat: 'plain',
      content: text,
      submessages: [
        { format: 'binary', subformat: `image/${ext}`, content: base64, label: filename ?? 'image' },
      ],
    };

    if (this.correlator) payload.submessages.push({ format: 'token', subformat: 'conversation', content: this.correlator });

    return this.sendPayloadAndExtract(payload);
  }

  // Send text with an arbitrary file attachment
  async sendWithFile(text: string, uri: string, filename?: string, mimeType?: string) {
    const base64 = await this.uriToBase64(uri);
    const subformat = mimeType ? mimeType : `file/${filename?.split('.').pop() ?? 'bin'}`;
    const payload: any = {
      format: 'text',
      subformat: 'plain',
      content: text,
      submessages: [
        { format: 'binary', subformat, content: base64, label: filename ?? 'file' },
      ],
    };

    if (this.correlator) payload.submessages.push({ format: 'token', subformat: 'conversation', content: this.correlator });

    return this.sendPayloadAndExtract(payload);
  }

  // Internal helper used by attachment methods to send payload and extract reply
  private async sendPayloadAndExtract(payload: any) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.baseUrl}/nlip/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const textBody = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${textBody || res.statusText}`);
      }
      const data = await res.json();

      if (Array.isArray(data?.submessages)) {
        const conv = data.submessages.find((s: any) => s?.format?.toLowerCase?.() === 'token' && s?.subformat?.toLowerCase?.().startsWith('conversation'));
        if (conv?.content) this.correlator = conv.content;
      }

      if (typeof data?.content === 'string' && data.content.trim().length > 0) return data.content;
      if (Array.isArray(data?.submessages)) {
        const firstText = data.submessages.find((s: any) => s?.format?.toLowerCase?.() === 'text' && typeof s?.content === 'string');
        if (firstText?.content) return firstText.content;
      }

      return typeof data === 'object' ? JSON.stringify(data) : String(data);
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err?.name === 'AbortError') throw new Error('Request timed out');
      throw err;
    }
  }
}
