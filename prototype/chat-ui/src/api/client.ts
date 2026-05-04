import { LoginResponse, ChatSession } from '../types';

const CORE_URL = import.meta.env.VITE_CORE_URL || 'http://localhost:8000';

class APIClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  clearToken() {
    this.token = null;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async login(): Promise<string> {
    // Avoid Content-Type: application/json on GET — that triggers a CORS preflight.
    const response = await fetch(`${CORE_URL}/auth/login`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }

    const data = (await response.json()) as { authorization_url: string };
    return data.authorization_url;
  }

  async devLogin(email: string): Promise<LoginResponse> {
    const response = await fetch(`${CORE_URL}/auth/dev-login?email=${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`Dev login failed: ${response.statusText}`);
    }

    return response.json() as Promise<LoginResponse>;
  }

  async sendMessage(message: string, sessionId?: string): Promise<ReadableStream<Uint8Array> | null> {
    const body = JSON.stringify({
      message,
      session_id: sessionId,
    });

    const response = await fetch(`${CORE_URL}/api/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body,
    });

    if (!response.ok) {
      throw new Error(`Chat failed: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('No response body');
    }

    return response.body;
  }

  async getChatHistory(): Promise<ChatSession[]> {
    const response = await fetch(`${CORE_URL}/api/chat/history`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch chat history: ${response.statusText}`);
    }

    const data = (await response.json()) as { sessions: ChatSession[] };
    return data.sessions;
  }
}

export const apiClient = new APIClient();
