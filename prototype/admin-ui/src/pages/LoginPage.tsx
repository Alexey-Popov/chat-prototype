import React, { useMemo, useState } from 'react';
import { adminApi } from '../api/client';

interface LoginPageProps {
  onLoginSuccess: (token: string) => void;
}

const demoEnabled = import.meta.env.VITE_DEV_MOCK_USER === 'true';
const defaultEmail =
  (import.meta.env.VITE_DEV_DEFAULT_EMAIL as string | undefined)?.trim() || 'dev@example.com';

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState(defaultEmail);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const docsUrl = useMemo(() => {
    const base = import.meta.env.VITE_ADMIN_URL || 'http://localhost:8002';
    return `${base}/docs`;
  }, []);

  const quickLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const r = await adminApi.devLogin(email.trim());
      adminApi.setToken(r.access_token);
      onLoginSuccess(r.access_token);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Login failed');
      setLoading(false);
    }
  };

  if (!demoEnabled) {
    return (
      <div style={styles.wrap}>
        <div style={styles.card}>
          <h1 style={styles.h1}>Admin</h1>
          <p style={styles.p}>
            Demo login is disabled. Set <code>VITE_DEV_MOCK_USER=true</code> at build time and{' '}
            <code>DEV_MOCK_USER</code> in <code>.env</code> on the admin API, then rebuild this image.
          </p>
          <a href={docsUrl} style={styles.link}>
            Open API docs
          </a>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.badge}>Demo mode</div>
        <h1 style={styles.h1}>Admin console</h1>
        <p style={styles.p}>
          Sign in with a dev user. The admin service grants the <strong>admin</strong> role and issues
          a JWT so you can manage users and roles.
        </p>
        <form onSubmit={quickLogin} style={styles.form}>
          <label style={styles.label}>Email</label>
          <input
            style={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <button type="submit" style={styles.btnPrimary} disabled={loading}>
            {loading ? 'Signing in…' : 'Demo sign-in'}
          </button>
          <button
            type="button"
            style={styles.btnGhost}
            disabled={loading || !defaultEmail}
            onClick={() => {
              setEmail(defaultEmail);
            }}
          >
            Use default demo email
          </button>
        </form>
        {err && <div style={styles.err}>{err}</div>}
        <p style={styles.footer}>
          <a href={docsUrl}>API reference (Swagger)</a>
        </p>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
    maxWidth: 420,
    width: '100%',
    padding: 32,
  },
  badge: {
    display: 'inline-block',
    background: '#e8f4fd',
    color: '#0b5cab',
    fontSize: 12,
    fontWeight: 600,
    padding: '4px 10px',
    borderRadius: 999,
    marginBottom: 16,
  },
  h1: { margin: '0 0 8px', fontSize: 24 },
  p: { margin: '0 0 20px', color: '#555', fontSize: 14 },
  form: { display: 'flex', flexDirection: 'column', gap: 10 },
  label: { fontSize: 13, fontWeight: 600 },
  input: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid #ccc',
    fontSize: 15,
  },
  btnPrimary: {
    marginTop: 8,
    padding: '12px 16px',
    borderRadius: 8,
    border: 'none',
    background: '#0d6efd',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 15,
  },
  btnGhost: {
    padding: '10px 16px',
    borderRadius: 8,
    border: '1px solid #ccc',
    background: '#fff',
    cursor: 'pointer',
    fontSize: 14,
  },
  err: {
    marginTop: 12,
    padding: 12,
    background: '#fde8e8',
    color: '#8b1a1a',
    borderRadius: 8,
    fontSize: 14,
  },
  footer: { marginTop: 20, fontSize: 13 },
  link: { color: '#0d6efd' },
};
