import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';

export interface UseAuthReturn {
  token: string | null;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  devLogin: (email: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
}

export function useAuth(): UseAuthReturn {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const authUrl = await apiClient.login();
      window.location.href = authUrl;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      setIsLoading(false);
    }
  }, []);

  const devLogin = useCallback(async (email: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.devLogin(email);
      const newToken = response.access_token;
      setToken(newToken);
      apiClient.setToken(newToken);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Dev login failed';
      setError(message);
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    apiClient.clearToken();
  }, []);

  return {
    token,
    isAuthenticated: token !== null,
    login,
    devLogin,
    logout,
    isLoading,
    error,
  };
}
