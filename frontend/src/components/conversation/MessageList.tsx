import React from 'react';
import { Message as MessageType } from '../../types/conversation';
import { flattenMessages } from '../../utils/conversationUtils';
import Message from './Message';

interface MessageListProps {
  messages: MessageType[];
  showThinking: {[messageId: string]: boolean};
  onToggleThinking: (messageId: string) => void;
  onRetry?: (messageId: string) => void;
  isRetrying?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  showThinking,
  onToggleThinking,
  onRetry,
  isRetrying
}) => {
  if (messages.length === 0) {
    return (
      <div className="no-messages">
        No messages in this conversation yet.
      </div>
    );
  }

  return (
    <div className="messages-container">
      {flattenMessages(messages).map((message, index) => (
        <Message
          key={message.message_id}
          message={message}
          index={index}
          showThinking={showThinking[message.message_id] || false}
          onToggleThinking={onToggleThinking}
          onRetry={onRetry}
          isRetrying={isRetrying}
        />
      ))}
    </div>
  );
};

export default MessageList;
