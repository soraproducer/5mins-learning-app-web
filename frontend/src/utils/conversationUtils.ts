import { Message, ParsedContent } from '../types/conversation';

// Flatten messages from the threaded structure to chronological order
export const flattenMessages = (messages: Message[]): Message[] => {
  const allMessages: Message[] = [];
  
  const addMessageAndReplies = (message: Message) => {
    allMessages.push(message);
    if (message.replies && message.replies.length > 0) {
      message.replies.forEach(reply => addMessageAndReplies(reply));
    }
  };
  
  messages.forEach(message => addMessageAndReplies(message));
  
  return allMessages;
  // Sort by timestamp to ensure chronological order
  // return allMessages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
};

// Helper function to check if flattened messages contain specific role
export const hasMessageWithRole = (messages: Message[], role: 'user' | 'assistant' | 'system'): boolean => {
  const flattened = flattenMessages(messages);
  return flattened.some((msg: Message) => msg.role === role);
};

// Format timestamp for display
export const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Parse message content to extract thinking and clean content
export const parseContent = (content: string): ParsedContent => {
  const thinkingRegex = /<think>([\s\S]*?)<\/think>/g;
  const thinkingMatches = content.match(thinkingRegex);
  const thinking = thinkingMatches ? thinkingMatches.map(match => match.replace(/<\/?think>/g, '').trim()) : [];
  
  // Simple content cleaning - preserve markdown structure
  let cleanContent = content
    .replace(thinkingRegex, '')
    .replace(/\\n/g, '\n')
    .replace(/\r\n/g, '\n')
    .replace(/ {2,}\n/g, '\n')
    .trim();
  
  return {
    thinking,
    cleanContent,
    hasThinking: thinking.length > 0
  };
};

// Format LLM metadata for display
export const formatLLMMetadata = (metadata: any, llmId?: string) => {
  const parts: string[] = [];
  
  // Add local LLM info
  if (llmId) {
    parts.push(`Local LLM: ${llmId}`);
  }
  
  // Add expert LLMs info from sources
  if (metadata && metadata.sources && Array.isArray(metadata.sources) && metadata.sources.length > 0) {
    parts.push(`Expert LLMs: ${metadata.sources.join(', ')}`);
  }
  
  return parts.length > 0 ? parts.join(' | ') : null;
};

// Rebuild hierarchical message structure from a flat array
export const rebuildHierarchicalStructure = (flatMessages: Message[]): Message[] => {
  const messageMap = new Map<string, Message>();
  const rootMessages: Message[] = [];
  
  // First pass: Create map of all messages
  flatMessages.forEach(msg => {
    messageMap.set(msg.message_id, { ...msg, replies: [] });
  });
  
  // Second pass: Build hierarchy
  flatMessages.forEach(msg => {
    const messageWithReplies = messageMap.get(msg.message_id)!;
    
    if (msg.parent_message_id) {
      const parent = messageMap.get(msg.parent_message_id);
      if (parent) {
        if (!parent.replies) parent.replies = [];
        parent.replies.push(messageWithReplies);
      }
    } else {
      rootMessages.push(messageWithReplies);
    }
  });
  
  return rootMessages;
};

// Add a message to the thread structure
export const addMessageToThread = (messages: Message[], newMessage: Message, parentMessageId?: string): Message[] => {
  if (!parentMessageId) {
    // If no parent, add as root message
    return [...messages, newMessage];
  }
  
  // Helper function to recursively find and update parent
  const addToParent = (msgList: Message[]): Message[] => {
    return msgList.map(msg => {
      if (msg.message_id === parentMessageId) {
        // Found the parent, add new message to its replies
        return {
          ...msg,
          replies: [...(msg.replies || []), newMessage]
        };
      } else if (msg.replies && msg.replies.length > 0) {
        // Recursively search in replies
        return {
          ...msg,
          replies: addToParent(msg.replies)
        };
      }
      return msg;
    });
  };
  
  return addToParent(messages);
};
