// Model configuration constants shared across components
export const EXPERT_LLM_OPTIONS = [
  { value: 'openai', label: 'OpenAI (GPT)' },
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'gemini', label: 'Gemini (Google)' }
];

export const LOCAL_MODEL_OPTIONS = [
  { value: 'gemma3:4b', label: 'Gemma3 4B (Faster)' },
  { value: 'gemma3:12b', label: 'Gemma3 12B (Better Quality)' },
  { value: 'deepseek-r1:8b', label: 'Deepseek R1 8B (Reasoning Model)' }
];

// Default selections
export const DEFAULT_EXPERT_PROVIDERS = ['openai', 'claude', 'gemini'];
export const DEFAULT_LOCAL_MODEL = 'gemma3:12b';
