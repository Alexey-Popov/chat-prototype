import { useCallback, useState } from 'react';
import { adminApi } from './api/client';
import { Dashboard } from './pages/Dashboard';
import { LoginPage } from './pages/LoginPage';

function App() {
  const [token, setToken] = useState<string | null>(null);

  const onLogin = useCallback((t: string) => {
    adminApi.setToken(t);
    setToken(t);
  }, []);

  const onLogout = useCallback(() => {
    adminApi.clearToken();
    setToken(null);
  }, []);

  if (!token) {
    return <LoginPage onLoginSuccess={onLogin} />;
  }

  return <Dashboard onLogout={onLogout} />;
}

export default App;
