const ADMIN_URL = import.meta.env.VITE_ADMIN_URL || 'http://localhost:8002';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserRow {
  id: string;
  email: string;
  oauth_sub: string;
  active: boolean;
  created_at: string;
}

export interface PaginatedUsers {
  items: UserRow[];
  total: number;
  page: number;
  size: number;
}

class AdminApiClient {
  private token: string | null = null;

  setToken(t: string) {
    this.token = t;
  }

  clearToken() {
    this.token = null;
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { Accept: 'application/json' };
    if (this.token) {
      h.Authorization = `Bearer ${this.token}`;
    }
    return h;
  }

  async devLogin(email: string): Promise<LoginResponse> {
    const q = new URLSearchParams({ email });
    const res = await fetch(`${ADMIN_URL}/auth/dev-login?${q}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t || res.statusText);
    }
    return res.json() as Promise<LoginResponse>;
  }

  async listUsers(page = 1, size = 20): Promise<PaginatedUsers> {
    const res = await fetch(
      `${ADMIN_URL}/api/admin/users?page=${page}&size=${size}`,
      { headers: this.headers() },
    );
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res.json() as Promise<PaginatedUsers>;
  }
}

export const adminApi = new AdminApiClient();
