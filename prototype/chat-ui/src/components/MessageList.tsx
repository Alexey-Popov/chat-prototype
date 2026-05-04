import React from 'react';
import { Message } from '../types';

interface MessageListProps {
  messages: Message[];
}

function renderMarkdown(content: string): string {
  let html = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');

  return html;
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div style={styles.container}>
      {messages.length === 0 ? (
        <div style={styles.empty}>
          <p>Start a conversation by typing a message below.</p>
        </div>
      ) : (
        messages.map((msg) => (
          <div key={msg.id} style={msg.role === 'user' ? styles.userMessage : styles.assistantMessage}>
            <div style={styles.messageBubble}>
              {msg.role === 'assistant' ? (
                <div
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                  style={styles.messageContent}
                />
              ) : (
                <div style={styles.messageContent}>{msg.content}</div>
              )}
            </div>
            <div style={styles.timestamp}>
              {new Date(msg.createdAt).toLocaleTimeString()}
            </div>
          </div>
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#999',
    fontSize: '16px',
  },
  userMessage: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
  },
  assistantMessage: {
    display: 'flex',
    justifyContent: 'flex-start',
    gap: '8px',
  },
  messageBubble: {
    maxWidth: '70%',
    padding: '12px 16px',
    borderRadius: '8px',
    wordWrap: 'break-word',
    lineHeight: '1.5',
  },
  userContent: {
    backgroundColor: '#007bff',
    color: 'white',
  },
  assistantContent: {
    backgroundColor: '#f0f0f0',
    color: '#333',
  },
  messageContent: {
    margin: 0,
  },
  timestamp: {
    fontSize: '12px',
    color: '#999',
    alignSelf: 'flex-end',
  },
};

// Apply user-specific styling
Object.assign(
  styles.userMessage,
  { ...styles.userMessage },
);
