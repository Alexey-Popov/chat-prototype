import React from 'react';
import { useChat } from '../hooks/useChat';
import { MessageList } from '../components/MessageList';
import { MessageInput } from '../components/MessageInput';

interface ChatPageProps {
  onLogout: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({ onLogout }) => {
  const { messages, isLoading, error, sendMessage } = useChat();

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Chat</h1>
        <button onClick={onLogout} style={styles.logoutButton}>
          Logout
        </button>
      </header>

      <MessageList messages={messages} />

      {error && (
        <div style={styles.errorBanner}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <MessageInput onSendMessage={sendMessage} isLoading={isLoading} />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: '#fff',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#f9f9f9',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    fontWeight: 'bold',
  },
  logoutButton: {
    padding: '8px 16px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  errorBanner: {
    padding: '12px 16px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    borderTop: '1px solid #f5c6cb',
    fontSize: '14px',
  },
};
