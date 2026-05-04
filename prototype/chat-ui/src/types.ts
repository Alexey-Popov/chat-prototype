export interface User {
  id: string;
  email: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  createdAt: string;
  messages: Message[];
}

export interface ChatHistoryResponse {
  sessions: ChatSession[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
