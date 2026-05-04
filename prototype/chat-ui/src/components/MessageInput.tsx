import React, { useState } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => Promise<void>;
  isLoading: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const content = message;
    setMessage('');
    await onSendMessage(content);
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
        disabled={isLoading}
        style={styles.input}
      />
      <button type="submit" disabled={isLoading || !message.trim()} style={styles.button}>
        {isLoading ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
};

const styles: Record<string, React.CSSProperties> = {
  form: {
    display: 'flex',
    gap: '8px',
    padding: '16px',
    backgroundColor: '#fff',
    borderTop: '1px solid #e0e0e0',
  },
  input: {
    flex: 1,
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'inherit',
    outline: 'none',
  },
  button: {
    padding: '12px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
};
