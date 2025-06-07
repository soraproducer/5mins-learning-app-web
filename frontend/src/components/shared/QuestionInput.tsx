import React from 'react';

interface QuestionInputProps {
  question: string;
  onQuestionChange: (question: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  placeholder?: string;
  submitButtonText?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

const QuestionInput: React.FC<QuestionInputProps> = ({
  question,
  onQuestionChange,
  onSubmit,
  placeholder = "What would you like to learn about?",
  submitButtonText = "Submit",
  disabled = false,
  autoFocus = false
}) => {
  return (
    <form onSubmit={onSubmit} className="question-form">
      <div className="input-container">
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder={placeholder}
          className="question-input"
          disabled={disabled}
          autoFocus={autoFocus}
        />
        <button 
          type="submit" 
          className="submit-button"
          disabled={!question.trim() || disabled}
        >
          {submitButtonText}
        </button>
      </div>
    </form>
  );
};

export default QuestionInput;
