import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';
import { Message, Conversation } from '../types/conversation';
import { flattenMessages, hasMessageWithRole, rebuildHierarchicalStructure, addMessageToThread } from '../utils/conversationUtils';
import { DEFAULT_EXPERT_PROVIDERS, DEFAULT_LOCAL_MODEL } from '../constants/modelOptions';

// Constants
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';
const API_BASE_URL = 'http://localhost:8000';

export const useConversation = () => {
  const [searchParams] = useSearchParams();
  const question = searchParams.get('q');
  const conversationId = searchParams.get('id');
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showThinking, setShowThinking] = useState<{[messageId: string]: boolean}>({});
  
  // Follow-up question state
  const [followUpQuestion, setFollowUpQuestion] = useState('');
  const [selectedProviders, setSelectedProviders] = useState<string[]>(DEFAULT_EXPERT_PROVIDERS);
  const [selectedLocalModel, setSelectedLocalModel] = useState(DEFAULT_LOCAL_MODEL);
  const [isSubmittingFollowUp, setIsSubmittingFollowUp] = useState(false);
  
  // Retry state
  const [isRetryingMessage, setIsRetryingMessage] = useState(false);
  
  // Guard to prevent duplicate conversation creation
  const isCreatingConversation = useRef(false);
  const hasCreatedConversation = useRef(false);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else if (question && !conversationId && !hasCreatedConversation.current && !isCreatingConversation.current) {
      // Handle new conversation creation from Home page
      createNewConversation();
    }
  }, [conversationId, question]);

  const pollForMessages = async (convId: string, existingMessageIds?: Set<string>, maxAttempts: number = 120) => {
    let attempts = 0;
    
    const poll = async () => {
      try {
        attempts++;
        
        const response = await fetch(`${API_BASE_URL}/api/conversations/${convId}/messages`);
        if (!response.ok) {
          throw new Error(`Failed to fetch messages: ${response.status}`);
        }
        
        const messagesData = await response.json();
        const flattenedMessages = flattenMessages(messagesData);
        
        // If no existing message IDs provided (new conversation), use original logic
        if (!existingMessageIds) {
          const hasUserMessage = hasMessageWithRole(messagesData, 'user');
          const hasAssistantMessage = hasMessageWithRole(messagesData, 'assistant');

          if (hasUserMessage && hasAssistantMessage) {
            // We have the complete conversation, update the UI
            setMessages(messagesData);
            setLoading(false);
            return;
          }
        } else {
          // For follow-up questions and retries, check if we have new assistant or system messages
          const currentMessageIds = new Set(flattenedMessages.map(msg => msg.message_id));
          
          // Find new messages that aren't in the existing set
          const newMessageIds = Array.from(currentMessageIds).filter(id => !existingMessageIds.has(id));
          
          // Check if any of the new messages are assistant or system messages
          const newMessages = flattenedMessages.filter(msg => newMessageIds.includes(msg.message_id));
          const hasNewAssistantOrSystemMessage = newMessages.some(msg => msg.role === 'assistant' || msg.role === 'system');
          
          if (hasNewAssistantOrSystemMessage) {
            // We have new assistant or system messages, update the UI
            setMessages(messagesData);
            setLoading(false);
            return;
          }
        }
        
        // Continue polling if we haven't reached max attempts
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000); // Poll every 1 second for better responsiveness
        } else {
          // Timeout reached
          setError('Response generation timed out. Please try again.');
          setLoading(false);
        }
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load messages');
        setLoading(false);
      }
    };
    
    // Start polling
    poll();
  };

  const createNewConversation = async () => {
    // Prevent duplicate calls
    if (isCreatingConversation.current || hasCreatedConversation.current) {
      return;
    }
    
    isCreatingConversation.current = true;
    
    try {
      setLoading(true);
      setError(null);

      if (!question) {
        throw new Error('No question provided');
      }

      // Get model parameters from URL
      const providers = searchParams.get('providers')?.split(',') || DEFAULT_EXPERT_PROVIDERS;
      const localModel = searchParams.get('localModel') || DEFAULT_LOCAL_MODEL;

      // Immediately show user's message in the UI
      const userMessage: Message = {
        message_id: 'temp-user-message',
        role: 'user',
        content: question,
        timestamp: new Date().toISOString()
      };
      
      // Show loading message for assistant
      const loadingMessage: Message = {
        message_id: 'temp-loading-message',
        role: 'assistant',
        content: '🔄 Thinking and analyzing your question...\n\nI\'m gathering information from multiple expert sources and preparing a comprehensive response.',
        timestamp: new Date().toISOString()
      };

      setMessages([userMessage, loadingMessage]);

      // Step 1: Create the conversation
      const conversationData = {
        topic: question,
        user_id: DEFAULT_USER_ID,
        user_name: 'User'
      };

      const createResponse = await fetch(`${API_BASE_URL}/api/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(conversationData),
      });

      if (!createResponse.ok) {
        throw new Error(`Failed to create conversation: ${createResponse.status}`);
      }

      const newConversation = await createResponse.json();
      
      // Mark as created to prevent duplicates
      hasCreatedConversation.current = true;
      
      // Set conversation info
      setConversation({
        conversation_id: newConversation.conversation_id,
        user_id: newConversation.user_id,
        user_name: newConversation.user_name,
        topic: newConversation.topic,
        created_at: newConversation.created_at,
        updated_at: newConversation.updated_at
      });

      // Step 2: Trigger the first reply
      const firstReplyData = {
        providers: providers,
        local_model_id: localModel
      };

      const firstReplyResponse = await fetch(`${API_BASE_URL}/api/conversations/${newConversation.conversation_id}/first-reply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(firstReplyData),
      });

      if (!firstReplyResponse.ok) {
        throw new Error(`Failed to trigger first reply: ${firstReplyResponse.status}`);
      }

      // Step 3: Poll for messages until assistant response is ready
      await pollForMessages(newConversation.conversation_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
      setLoading(false);
      // Reset flags on error to allow retry
      hasCreatedConversation.current = false;
    } finally {
      isCreatingConversation.current = false;
    }
  };

  const loadConversation = async (id: string) => {
    try {
      setLoading(true);
      setError(null);

      // Fetch messages
      const messagesResponse = await fetch(`${API_BASE_URL}/api/conversations/${id}/messages`);
      if (!messagesResponse.ok) {
        throw new Error(`Failed to fetch messages: ${messagesResponse.status}`);
      }
      const messagesData = await messagesResponse.json();
      setMessages(messagesData);

      // For now, we'll extract conversation info from the first message or create a basic one
      // In a full implementation, you might want a separate endpoint for conversation details
      setConversation({
        conversation_id: id,
        user_id: '',
        user_name: '',
        topic: messagesData.length > 0 ? messagesData[0].content : 'Conversation',
        created_at: messagesData.length > 0 ? messagesData[0].timestamp : new Date().toISOString(),
        updated_at: messagesData.length > 0 ? messagesData[messagesData.length - 1].timestamp : new Date().toISOString()
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  };

  const submitFollowUpQuestion = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!followUpQuestion.trim()) {
      console.log("Early return: followUpQuestion is empty");
      return;
    }
    
    if (!conversation?.conversation_id) {
      console.log("Early return: no conversation ID");
      return;
    }
    
    if (isSubmittingFollowUp) {
      console.log("Early return: already submitting");
      return;
    }

    try {
      setIsSubmittingFollowUp(true);
      setError(null);

      // Collect existing message IDs before adding temporary messages
      const existingMessageIds = new Set(
        flattenMessages(messages)
          .map(msg => msg.message_id)
          .filter(id => !id.startsWith('temp-')) // Exclude any existing temp messages
      );

      // Immediately show user's message in the UI
      const userMessage: Message = {
        message_id: `temp-user-message-${Date.now()}`,
        role: 'user',
        content: followUpQuestion,
        timestamp: new Date().toISOString()
      };
      
      // Show loading message for assistant
      const loadingMessage: Message = {
        message_id: `temp-loading-message-${Date.now()}`,
        role: 'assistant',
        content: '🔄 Processing your follow-up question...\n\nI\'m gathering information from multiple expert sources and preparing a comprehensive response.',
        timestamp: new Date().toISOString()
      };

      // Remove any existing temporary messages and add new ones
      setMessages(prev => {
        // Filter out any existing temporary messages
        const filteredMessages = prev.filter(msg => !msg.message_id.startsWith('temp-'));
        // Add new temporary messages at the end
        return [...filteredMessages, userMessage, loadingMessage];
      });

      // Clear the input
      setFollowUpQuestion('');

      // Submit follow-up question to backend
      const replyData = {
        message_content: followUpQuestion,
        providers: selectedProviders,
        local_model_id: selectedLocalModel
      };
      
      const response = await fetch(`${API_BASE_URL}/api/conversations/${conversation.conversation_id}/reply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(replyData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to submit follow-up question: ${response.status} - ${errorText}`);
      }

      // Start polling for the updated conversation with existing message IDs
      await pollForMessages(conversation.conversation_id, existingMessageIds);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit follow-up question');
      // Remove the temporary loading message on error
      setMessages(prev => prev.filter(m => !m.message_id.startsWith('temp-loading-message')));
    } finally {
      setIsSubmittingFollowUp(false);
    }
  };

  const toggleThinking = (messageId: string) => {
    setShowThinking(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const handleProviderChange = (provider: string) => {
    setSelectedProviders(prev => {
      if (prev.includes(provider)) {
        // Remove if already selected, but ensure at least one is selected
        const newProviders = prev.filter(p => p !== provider);
        return newProviders.length > 0 ? newProviders : prev;
      } else {
        // Add if not selected
        return [...prev, provider];
      }
    });
  };

  const retryMessage = async (messageId: string) => {
    if (!conversation?.conversation_id) {
      setError('No conversation available');
      return;
    }

    if (isRetryingMessage) {
      return; // Already retrying
    }

    try {
      setIsRetryingMessage(true);
      setError(null);

      // Helper function to find message index in flat structure
      const findMessageIndex = (msgs: Message[], msgId: string): number => {
        const flatMessages = flattenMessages(msgs);
        return flatMessages.findIndex(msg => msg.message_id === msgId);
      };

      // Find the target message and determine which messages to remove
      const targetIndex = findMessageIndex(messages, messageId);
      if (targetIndex === -1) {
        throw new Error('Message to retry not found');
      }

      // Get the flat message array and find all messages from target index onwards
      const flatMessages = flattenMessages(messages);
      const targetMessage = flatMessages[targetIndex];
      
      // Immediately remove the target message and all subsequent messages from UI
      // We need to rebuild the hierarchical structure without the target and subsequent messages
      const messagesToKeep = flatMessages.slice(0, targetIndex);
      
      // Rebuild hierarchical structure for remaining messages
      const rebuiltMessages = rebuildHierarchicalStructure(messagesToKeep);
      
      // Add loading message to show retry progress
      const loadingMessage: Message = {
        message_id: `temp-retry-loading-${Date.now()}`,
        role: 'assistant',
        content: '🔄 Regenerating response with different models...\n\nI\'m gathering fresh information from the selected expert sources.',
        timestamp: new Date().toISOString()
      };

      // Find the parent message to attach the loading message
      const parentMessage = flatMessages.find(msg => msg.message_id === targetMessage.parent_message_id);
      if (parentMessage) {
        // Add loading message as a reply to the parent
        const updatedMessages = addMessageToThread(rebuiltMessages, loadingMessage, targetMessage.parent_message_id);
        setMessages(updatedMessages);
      } else {
        // If no parent found, just append to the end
        setMessages([...rebuiltMessages, loadingMessage]);
      }

      // Collect remaining message IDs to track when retry is complete
      const remainingMessageIds = new Set(
        messagesToKeep
          .map(msg => msg.message_id)
          .filter(id => !id.startsWith('temp-'))
      );

      // Call the retry endpoint
      const retryData = {
        providers: selectedProviders,
        local_model_id: selectedLocalModel
      };

      const response = await fetch(`${API_BASE_URL}/api/messages/${messageId}/retry`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(retryData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to retry message: ${response.status} - ${errorText}`);
      }

      // Poll for the updated conversation with remaining message IDs (shorter timeout for retries)
      await pollForMessages(conversation.conversation_id, remainingMessageIds, 120);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry message');
      // Remove loading message on error
      setMessages(prev => prev.filter(m => !m.message_id.startsWith('temp-retry-loading')));
    } finally {
      setIsRetryingMessage(false);
    }
  };

  return {
    // State
    messages,
    conversation,
    loading,
    error,
    showThinking,
    followUpQuestion,
    selectedProviders,
    selectedLocalModel,
    isSubmittingFollowUp,
    question,
    conversationId,
    isRetryingMessage,
    
    // Actions
    setFollowUpQuestion,
    setSelectedLocalModel,
    submitFollowUpQuestion,
    toggleThinking,
    handleProviderChange,
    retryMessage
  };
};
