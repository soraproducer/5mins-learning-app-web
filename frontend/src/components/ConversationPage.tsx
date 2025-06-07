import React from 'react';
import './ConversationPage.css';
import { useConversation } from '../hooks/useConversation';
import ConversationHeader from './conversation/ConversationHeader';
import MessageList from './conversation/MessageList';
import QuestionInput from './shared/QuestionInput';
import ModelSelection from './shared/ModelSelection';

const ConversationPage: React.FC = () => {
  const {
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
    setFollowUpQuestion,
    setSelectedLocalModel,
    submitFollowUpQuestion,
    toggleThinking,
    handleProviderChange,
    retryMessage
  } = useConversation();

  if (loading && messages.length === 0) {
    return (
      <div className="conversation-page">
        <div className="conversation-container">
          <h1 className="conversation-title">Loading Conversation...</h1>
        </div>
      </div>
    );
  }

  if (error && messages.length === 0) {
    return (
      <div className="conversation-page">
        <div className="conversation-container">
          <h1 className="conversation-title">Error</h1>
          <div className="error-message">
            {error}
          </div>
        </div>
      </div>
    );
  }

  // Handle new question case (from Home page) OR existing conversation with messages
  if ((question && !conversationId) || (conversation && messages.length > 0)) {
    return (
      <div className="conversation-page">
        <div className="conversation-container">
          <ConversationHeader conversation={conversation} />
          
          {/* Model selection between header and messages */}
          {conversation && (
            <div className="model-selection-container">
              <ModelSelection
                selectedProviders={selectedProviders}
                selectedLocalModel={selectedLocalModel}
                onProviderChange={handleProviderChange}
                onLocalModelChange={setSelectedLocalModel}
                disabled={isSubmittingFollowUp}
              />
            </div>
          )}
          
          <MessageList
            messages={messages}
            showThinking={showThinking}
            onToggleThinking={toggleThinking}
            onRetry={retryMessage}
            isRetrying={isRetryingMessage}
          />
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {/* Follow-up question form */}
          {conversation && (
            <div className="follow-up-form">
              <QuestionInput
                question={followUpQuestion}
                onQuestionChange={setFollowUpQuestion}
                onSubmit={submitFollowUpQuestion}
                placeholder="Ask a follow-up question..."
                submitButtonText={isSubmittingFollowUp ? 'Sending...' : 'Send'}
                disabled={isSubmittingFollowUp}
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  // Handle conversation loading case (from History page)
  if (conversationId && conversation) {
    return (
      <div className="conversation-page">
        <div className="conversation-container">
          <ConversationHeader conversation={conversation} />
          
          {/* Model selection between header and messages */}
          <div className="model-selection-container">
            <ModelSelection
              selectedProviders={selectedProviders}
              selectedLocalModel={selectedLocalModel}
              onProviderChange={handleProviderChange}
              onLocalModelChange={setSelectedLocalModel}
              disabled={isSubmittingFollowUp}
            />
          </div>
          
          <MessageList
            messages={messages}
            showThinking={showThinking}
            onToggleThinking={toggleThinking}
            onRetry={retryMessage}
            isRetrying={isRetryingMessage}
          />

          {/* Follow-up question form */}
          <div className="follow-up-form">
            <QuestionInput
              question={followUpQuestion}
              onQuestionChange={setFollowUpQuestion}
              onSubmit={submitFollowUpQuestion}
              placeholder="Ask a follow-up question..."
              submitButtonText={isSubmittingFollowUp ? 'Sending...' : 'Send'}
              disabled={isSubmittingFollowUp}
            />
          </div>
        </div>
      </div>
    );
  }

  // Default case
  return (
    <div className="conversation-page">
      <div className="conversation-container">
        <ConversationHeader conversation={null} />
        <p className="conversation-placeholder">
          No conversation selected.
        </p>
      </div>
    </div>
  );
};

export default ConversationPage;
