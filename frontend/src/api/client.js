import axios from 'axios';

// Vite uses import.meta.env.VITE_* (not process.env.REACT_APP_*)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
  }
});

export const detectAPI = {
  // JIE Detection
  jieDetect: (samples, targetSamples, mode = 'sync') =>
    api.post('/api/detect', {
      samples,
      target_samples: targetSamples,
      mode,
    }),

  // RLOD Detection
  rlodDetect: (samples, cleanSamples, mode = 'sync') =>
    api.post('/api/detect/rlod', {
      samples,
      target_samples: cleanSamples,
      mode,
    }),

  // Combined Detection
  combinedDetect: (samples, targetSamples, mode = 'sync') =>
    api.post('/api/detect/combined', {
      samples,
      target_samples: targetSamples,
      mode,
    }),

  // Get Job Status
  getJobStatus: (jobId) =>
    api.get(`/api/jobs/${jobId}`),

  // Health Check
  health: () =>
    api.get('/health'),

  // Readiness Check
  ready: () =>
    api.get('/ready'),

  // Get Metrics
  metrics: () =>
    api.get('/metrics'),
};

export const chatAPI = {
  // Send message to chatbot
  sendMessage: (message, conversationId) =>
    api.post('/api/chat', {
      message,
      conversation_id: conversationId,
    }),

  // Get conversation history
  getHistory: (conversationId) =>
    api.get(`/api/chat/history/${conversationId}`),

  // Create new conversation
  createConversation: () =>
    api.post('/api/chat/conversation', {}),
};

export default api;
