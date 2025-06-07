import React from 'react';
import { Conversation } from '../../types/conversation';
import { formatTimestamp } from '../../utils/conversationUtils';

interface ConversationHeaderProps {
  conversation: Conversation | null;
  isNewConversation?: boolean;
}

const ConversationHeader: React.FC<ConversationHeaderProps> = ({
  conversation,
  isNewConversation = false
}) => {
  return (
    <div className="conversation-header">
      <h1 className="conversation-title">
        {conversation ? conversation.topic : 'New Conversation'}
      </h1>
      {conversation && (
        <div className="conversation-info">
          <span className="conversation-date">
            Started: {formatTimestamp(conversation.created_at)}
          </span>
        </div>
      )}
    </div>
  );
};

export default ConversationHeader;
