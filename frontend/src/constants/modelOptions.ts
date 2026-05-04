// Model configuration constants shared across components
export const EXPERT_LLM_OPTIONS = [
  { value: 'openai', label: 'OpenAI (GPT)' },
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'gemini', label: 'Gemini (Google)' }
];

export const LOCAL_MODEL_OPTIONS = [
  { value: 'gemma3:4b', label: 'Gemma 3 4B (Default)' },
  { value: 'gemma3:12b', label: 'Gemma 3 12B (Higher Quality)' },
  { value: 'qwen3:4b', label: 'Qwen3 4B (Long Context)' },
  { value: 'llama3.2:3b', label: 'Llama 3.2 3B (Lightweight)' }
];

// Default selections
export const DEFAULT_EXPERT_PROVIDERS = ['openai', 'claude', 'gemini'];
export const DEFAULT_LOCAL_MODEL = 'gemma3:4b';
