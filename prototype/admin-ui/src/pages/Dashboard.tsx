import React, { useEffect, useState } from 'react';
import { adminApi, type UserRow } from '../api/client';

interface DashboardProps {
  onLogout: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onLogout }) => {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await adminApi.listUsers(1, 50);
        if (!cancelled) {
          setUsers(data.items);
          setTotal(data.total);
        }
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : 'Failed to load users');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const docs =
    (import.meta.env.VITE_ADMIN_URL || 'http://localhost:8002') + '/docs';

  return (
    <div style={styles.layout}>
      <header style={styles.header}>
        <div>
          <strong>Admin</strong>
          <span style={styles.muted}> · {total} users</span>
        </div>
        <div style={styles.actions}>
          <a href={docs} target="_blank" rel="noreferrer" style={styles.a}>
            API docs
          </a>
          <button type="button" style={styles.outline} onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>
      <main style={styles.main}>
        {loading && <p>Loading users…</p>}
        {err && <p style={{ color: '#b00020' }}>{err}</p>}
        {!loading && !err && (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Active</th>
                <th style={styles.th}>Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={styles.td}>{u.email}</td>
                  <td style={styles.td}>{u.active ? 'yes' : 'no'}</td>
                  <td style={styles.td}>{u.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  layout: { minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    background: '#fff',
    borderBottom: '1px solid #e5e5e5',
  },
  muted: { color: '#666', fontWeight: 400, marginLeft: 8 },
  actions: { display: 'flex', gap: 12, alignItems: 'center' },
  a: { color: '#0d6efd', fontSize: 14 },
  outline: {
    padding: '8px 14px',
    borderRadius: 8,
    border: '1px solid #ccc',
    background: '#fff',
    cursor: 'pointer',
  },
  main: { flex: 1, padding: 24 },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: '#fff',
    borderRadius: 8,
    overflow: 'hidden',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  th: {
    textAlign: 'left',
    padding: '12px 16px',
    background: '#f8f9fa',
    fontSize: 13,
    borderBottom: '1px solid #eee',
  },
  td: { padding: '12px 16px', fontSize: 14, borderBottom: '1px solid #f0f0f0' },
};
