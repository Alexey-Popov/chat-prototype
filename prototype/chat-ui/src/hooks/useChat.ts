import { useState, useCallback, useRef } from 'react';
import { Message } from '../types';
import { apiClient } from '../api/client';

interface StreamMessage {
  token?: string;
  done?: boolean;
  error?: string;
}

export interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;
  sendMessage: (content: string) => Promise<void>;
}

function parseSSELine(line: string): StreamMessage | null {
  if (!line.startsWith('data: ')) {
    return null;
  }
  try {
    return JSON.parse(line.slice(6)) as StreamMessage;
  } catch {
    return null;
  }
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState<string | null>(null);
  const currentResponseRef = useRef<string>('');
  const messageIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setError(null);
    setIsLoading(true);
    currentResponseRef.current = '';

    try {
      // Add user message to state
      const userMessageId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        {
          id: userMessageId,
          role: 'user',
          content,
          createdAt: new Date().toISOString(),
        },
      ]);

      // Create assistant message placeholder
      const assistantMessageId = crypto.randomUUID();
      messageIdRef.current = assistantMessageId;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          createdAt: new Date().toISOString(),
        },
      ]);

      const stream = await apiClient.sendMessage(content, sessionId ?? undefined);
      if (!stream) {
        throw new Error('No stream returned');
      }

      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const message = parseSSELine(line);
          if (!message) continue;

          if (message.token) {
            currentResponseRef.current += message.token;
            setMessages((prev) => {
              const copy = [...prev];
              const lastMsg = copy[copy.length - 1];
              if (lastMsg && lastMsg.id === assistantMessageId) {
                lastMsg.content = currentResponseRef.current;
              }
              return copy;
            });
          } else if (message.error) {
            throw new Error(message.error);
          } else if (message.done) {
            // Stream complete
          }
        }
      }

      // Process any remaining buffer
      if (buffer) {
        const message = parseSSELine(buffer);
        if (message?.token) {
          currentResponseRef.current += message.token;
          setMessages((prev) => {
            const copy = [...prev];
            const lastMsg = copy[copy.length - 1];
            if (lastMsg && lastMsg.id === assistantMessageId) {
              lastMsg.content = currentResponseRef.current;
            }
            return copy;
          });
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send message';
      setError(message);
      // Remove the incomplete assistant message on error
      setMessages((prev) => prev.filter((m) => m.id !== messageIdRef.current));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  return {
    messages,
    isLoading,
    error,
    sessionId,
    sendMessage,
  };
}
