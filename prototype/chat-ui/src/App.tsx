import { useState, useEffect, useCallback } from 'react';
import { LoginPage } from './pages/LoginPage';
import { ChatPage } from './pages/ChatPage';
import { apiClient } from './api/client';

/**
 * Token lives here (in memory only — never localStorage).
 * Auth state is lifted to App so the OAuth callback can hydrate it
 * via URL param and immediately flip isAuthenticated without the
 * useAuth hook holding a separate copy.
 */
function App() {
  const [token, setToken] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    // OAuth callback: core redirects to /?token=<jwt>
    const params = new URLSearchParams(window.location.search);
    const callbackToken = params.get('token');
    if (callbackToken) {
      apiClient.setToken(callbackToken);
      setToken(callbackToken);
      // Clean up URL so a refresh doesn't re-use the same token param
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    setIsInitialized(true);
  }, []);

  const handleLoginSuccess = useCallback((newToken: string) => {
    apiClient.setToken(newToken);
    setToken(newToken);
  }, []);

  const handleLogout = useCallback(() => {
    apiClient.clearToken();
    setToken(null);
  }, []);

  if (!isInitialized) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        Loading…
      </div>
    );
  }

  if (!token) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return <ChatPage onLogout={handleLogout} />;
}

export default App;
