import React, { useState } from 'react';
import { apiClient } from '../api/client';

interface LoginPageProps {
  onLoginSuccess: (token: string) => void;
}

const demoUiEnabled = import.meta.env.VITE_DEV_MOCK_USER === 'true';
const bakedDefaultEmail = (import.meta.env.VITE_DEV_DEFAULT_EMAIL || '').trim();

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [devEmail, setDevEmail] = useState(
    bakedDefaultEmail || 'dev@example.com',
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOAuthLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const authUrl = await apiClient.login();
      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsLoading(false);
    }
  };

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.devLogin(devEmail.trim());
      onLoginSuccess(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dev login failed');
      setIsLoading(false);
    }
  };

  const oneClickDemo = async () => {
    const email = bakedDefaultEmail || devEmail.trim();
    if (!email) {
      setError('Set DEV_MOCK_USER in .env or enter an email.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.devLogin(email);
      onLoginSuccess(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dev login failed');
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Chat System</h1>
        <p style={styles.subtitle}>Sign in to your account</p>

        {demoUiEnabled && (
          <>
            <div style={styles.demoBanner}>
              <strong>Demo mode</strong>
              <span style={styles.demoHint}>
                {' '}
                — uses core <code style={styles.code}>DEV_MOCK_USER</code> / dev-login. No Google account
                required.
              </span>
            </div>
            <button
              type="button"
              onClick={oneClickDemo}
              style={styles.demoPrimary}
              disabled={isLoading}
            >
              {isLoading ? 'Signing in…' : bakedDefaultEmail ? `Continue as ${bakedDefaultEmail}` : 'Demo sign-in (current email)'}
            </button>
            <form onSubmit={handleDevLogin} style={styles.form}>
              <label style={styles.label}>Or enter any email for dev JWT</label>
              <input
                type="email"
                value={devEmail}
                onChange={(e) => setDevEmail(e.target.value)}
                placeholder="dev@example.com"
                style={styles.input}
              />
              <button type="submit" style={styles.secondaryButton} disabled={isLoading}>
                {isLoading ? 'Loading…' : 'Dev sign-in with email above'}
              </button>
            </form>
            <div style={styles.divider}>OAuth (optional)</div>
          </>
        )}

        <form onSubmit={handleOAuthLogin} style={styles.form}>
          <button type="submit" style={styles.primaryButton} disabled={isLoading}>
            {isLoading ? 'Loading…' : 'Login with Google OAuth'}
          </button>
          {demoUiEnabled && (
            <p style={styles.oauthNote}>Use this when you have configured real OAuth client credentials.</p>
          )}
        </form>

        {error && <div style={styles.error}>{error}</div>}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: 16,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    padding: '40px',
    width: '100%',
    maxWidth: '440px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    margin: '0 0 8px 0',
    color: '#333',
  },
  subtitle: {
    fontSize: '14px',
    color: '#666',
    margin: '0 0 20px 0',
  },
  demoBanner: {
    background: '#e8f4fd',
    color: '#0b3d6d',
    padding: '12px 14px',
    borderRadius: 8,
    fontSize: 13,
    marginBottom: 16,
    lineHeight: 1.45,
  },
  demoHint: { fontWeight: 400 },
  code: { fontSize: 12 },
  demoPrimary: {
    width: '100%',
    padding: '14px 16px',
    backgroundColor: '#0d6efd',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
    marginBottom: 20,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  label: { fontSize: 12, fontWeight: 600, color: '#444' },
  input: {
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'inherit',
  },
  primaryButton: {
    padding: '12px 16px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  secondaryButton: {
    padding: '12px 16px',
    backgroundColor: '#6c757d',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '15px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  divider: {
    textAlign: 'center',
    color: '#999',
    margin: '20px 0',
    fontSize: '13px',
  },
  oauthNote: {
    margin: 0,
    fontSize: 12,
    color: '#666',
  },
  error: {
    marginTop: '12px',
    padding: '12px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    borderRadius: '4px',
    fontSize: '14px',
  },
};
