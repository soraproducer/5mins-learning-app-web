import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import './HistoryPage.css';

interface Conversation {
  conversation_id: string;
  user_id: string;
  user_name: string;
  topic: string;
  created_at: string;
  updated_at: string;
  messages: any[];
}

const HistoryPage: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Using the test user ID from the database
  const userId = "00000000-0000-0000-0000-000000000000";

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:8000/api/conversations/user/${userId}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch conversations: ${response.status}`);
        }
        
        const data = await response.json();
        setConversations(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversations');
      } finally {
        setLoading(false);
      }
    };

    fetchConversations();
  }, [userId]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleDeleteConversation = async (conversationId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent navigation to conversation page
    try {
      const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete conversation: ${response.status}`);
      }

      // Remove the conversation from the local state
      setConversations(conversations.filter(conv => conv.conversation_id !== conversationId));
      setOpenDropdown(null);
    } catch (err) {
      console.error('Error deleting conversation:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete conversation');
    }
  };

  const toggleDropdown = (conversationId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setOpenDropdown(openDropdown === conversationId ? null : conversationId);
  };

  const handleConversationClick = (conversationId: string) => {
    navigate(`/conversation?id=${conversationId}`);
  };

  if (loading) {
    return (
      <div className="history-page">
        <div className="history-container">
          <h1 className="history-title">Conversation History</h1>
          <div className="loading-message">Loading conversations...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-page">
        <div className="history-container">
          <h1 className="history-title">Conversation History</h1>
          <div className="error-message">Error: {error}</div>
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="history-page">
        <div className="history-container">
          <h1 className="history-title">Conversation History</h1>
          <div className="empty-message">No conversations yet. Start a new conversation from the Home page!</div>
        </div>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="history-container">
        <h1 className="history-title">Conversation History</h1>
        <div className="conversations-list">
          {conversations.map((conversation) => (
            <div 
              key={conversation.conversation_id} 
              className="conversation-item"
              onClick={() => handleConversationClick(conversation.conversation_id)}
              style={{ cursor: 'pointer' }}
            >
              <div className="conversation-content">
                <div className="conversation-left">
                  <div className="conversation-summary">
                    {truncateText(conversation.topic)}
                  </div>
                  <div className="conversation-meta">
                    <span className="conversation-date">
                      {formatDate(conversation.updated_at)}
                    </span>
                  </div>
                </div>
                <div className="conversation-actions">
                  <button
                    className="menu-button"
                    onClick={(e) => toggleDropdown(conversation.conversation_id, e)}
                  >
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="5" r="2"/>
                      <circle cx="12" cy="12" r="2"/>
                      <circle cx="12" cy="19" r="2"/>
                    </svg>
                  </button>
                  {openDropdown === conversation.conversation_id && (
                    <div className="dropdown-menu" ref={dropdownRef}>
                      <button
                        className="dropdown-item delete"
                        onClick={(e) => handleDeleteConversation(conversation.conversation_id, e)}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
