export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  parent_message_id?: string;
  llm_id?: string;
  llm_metadata?: any;
  replies?: Message[];
}

export interface Conversation {
  conversation_id: string;
  user_id: string;
  user_name: string;
  topic: string;
  created_at: string;
  updated_at: string;
}

export interface ParsedContent {
  thinking: string[];
  cleanContent: string;
  hasThinking: boolean;
}
