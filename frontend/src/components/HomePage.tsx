import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import './HomePage.css';
import { DEFAULT_EXPERT_PROVIDERS, DEFAULT_LOCAL_MODEL } from '../constants/modelOptions';
import QuestionInput from './shared/QuestionInput';
import ModelSelection from './shared/ModelSelection';

const HomePage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [selectedProviders, setSelectedProviders] = useState<string[]>(DEFAULT_EXPERT_PROVIDERS);
  const [selectedLocalModel, setSelectedLocalModel] = useState(DEFAULT_LOCAL_MODEL);
  const navigate = useNavigate();

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (question.trim()) {
      // Pass the selected models as URL parameters
      const params = new URLSearchParams({
        q: question,
        providers: selectedProviders.join(','),
        localModel: selectedLocalModel
      });
      
      console.log('Question submitted:', {
        question,
        providers: selectedProviders,
        localModel: selectedLocalModel
      });
      
      navigate(`/conversation?${params.toString()}`);
    }
  };

  return (
    <div className="home-page">
      <div className="home-container">
        <div className="home-header">
          <h1 className="home-title">5-Minute Learning</h1>
          <p className="home-subtitle">
            Learn the basics of any topic in around 5 minutes
          </p>
        </div>
        
        <QuestionInput
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
          placeholder="What would you like to learn about? (e.g., &quot;The difference between PPO and GRPO&quot;)"
          submitButtonText="Learn"
          autoFocus={true}
        />
        
        <ModelSelection
          selectedProviders={selectedProviders}
          selectedLocalModel={selectedLocalModel}
          onProviderChange={handleProviderChange}
          onLocalModelChange={setSelectedLocalModel}
        />
        
        <div className="examples">
          <p className="examples-label">Example questions:</p>
          <div className="example-items">
            <button 
              className="example-button"
              onClick={() => setQuestion("The impact of the appreciation of the US dollar")}
            >
              The impact of the appreciation of the US dollar
            </button>
            <button 
              className="example-button"
              onClick={() => setQuestion("The history of Nike vs Adidas")}
            >
              The history of Nike vs Adidas
            </button>
            <button 
              className="example-button"
              onClick={() => setQuestion("The difference between PPO and GRPO")}
            >
              The difference between PPO and GRPO
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
