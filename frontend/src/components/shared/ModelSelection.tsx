import React from 'react';
import { EXPERT_LLM_OPTIONS, LOCAL_MODEL_OPTIONS } from '../../constants/modelOptions';

interface ModelSelectionProps {
  selectedProviders: string[];
  selectedLocalModel: string;
  onProviderChange: (provider: string) => void;
  onLocalModelChange: (model: string) => void;
  disabled?: boolean;
}

const ModelSelection: React.FC<ModelSelectionProps> = ({
  selectedProviders,
  selectedLocalModel,
  onProviderChange,
  onLocalModelChange,
  disabled = false
}) => {
  return (
    <div className="model-selection">
      <div className="model-group">
        <label className="model-label">Expert LLMs (Multiple):</label>
        <div className="custom-multiselect">
          <div className="multiselect-display">
            {selectedProviders.length === EXPERT_LLM_OPTIONS.length 
              ? "All Selected" 
              : selectedProviders.map(provider => 
                  EXPERT_LLM_OPTIONS.find(opt => opt.value === provider)?.label
                ).join(", ")
            }
          </div>
          <div className="multiselect-options">
            {EXPERT_LLM_OPTIONS.map(option => (
              <label key={option.value} className="multiselect-option">
                <input
                  type="checkbox"
                  checked={selectedProviders.includes(option.value)}
                  onChange={() => onProviderChange(option.value)}
                  className="multiselect-checkbox"
                  disabled={disabled}
                />
                <span className="multiselect-text">{option.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
      
      <div className="model-group">
        <label className="model-label">Local Model (Single):</label>
        <select
          value={selectedLocalModel}
          onChange={(e) => onLocalModelChange(e.target.value)}
          className="model-select"
          disabled={disabled}
        >
          {LOCAL_MODEL_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default ModelSelection;
