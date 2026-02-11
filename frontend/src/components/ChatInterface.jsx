import React, { useState } from 'react';
import { Send, Copy, Check } from 'lucide-react';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: 'Hello! I am the AI Poison Guard Assistant. I can help you understand the system detection results, analyze trends, and provide recommendations for mitigating data poisoning attacks. What would you like to know?',
      sender: 'assistant',
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage = {
        id: messages.length + 2,
        text: generateResponse(inputValue),
        sender: 'assistant',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 800);
  };

  const generateResponse = (input) => {
    const lowerInput = input.toLowerCase();

    if (lowerInput.includes('suspicious') || lowerInput.includes('detect')) {
      return 'Based on the latest analysis, we detected 12 suspicious samples in the training data. The combined JIE+RLOD score identified these with 94% confidence. I recommend applying mitigation weights to reduce their influence during the next training epoch.';
    } else if (lowerInput.includes('score') || lowerInput.includes('result')) {
      return 'The average detection score is 0.42, indicating the majority of samples are clean. However, 3% of samples have scores above 0.7, suggesting potential poisoning. Would you like me to provide detailed analysis of these samples?';
    } else if (lowerInput.includes('recommendation') || lowerInput.includes('suggest')) {
      return 'Here are my recommendations:\n1. Increase the influence threshold to 0.75 for JIE detection\n2. Use FAISS GPU acceleration for faster RLOD analysis\n3. Monitor detection metrics every 2 epochs\n4. Consider retraining on filtered samples with adjusted weights';
    } else if (lowerInput.includes('how') && lowerInput.includes('work')) {
      return 'The system uses two complementary detection methods:\n\n1. JIE (Joint Influence Estimation): Uses TracIn algorithm with gradient-based influence scoring to identify samples that most affect model predictions.\n\n2. RLOD (Representation-Level Outlier Detection): Analyzes embeddings in hidden layers using kNN, spectral, and clustering methods to find anomalous representations.\n\nThese are combined (60% JIE + 40% RLOD) for robust detection.';
    } else {
      return 'That\'s an interesting question! Based on the current detection results, I can help analyze metrics, explain detection methods, provide recommendations for improving defense mechanisms, or discuss specific sample behaviors. What aspect would you like to explore further?';
    }
  };

  const copyToClipboard = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col h-full" style={{ background: 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%)' }}>
      {/* Header */}
      <div className="border-b border-primary/30 p-6 shadow-sm" style={{ background: 'linear-gradient(135deg, rgba(131, 56, 236, 0.1) 0%, rgba(10, 10, 15, 0.95) 100%)', backdropFilter: 'blur(10px)' }}>
        <h2 className="text-3xl font-bold text-white gta-glow mb-2">🤖 AI Assistant</h2>
        <p className="text-base text-gray-300">Poison Guard Detection Analyzer</p>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`chat-message ${message.sender}`}>
            <div className="flex gap-2 items-start max-w-2xl">
              <div className={`message-content ${message.sender}`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
                <p className="text-xs opacity-70 mt-1">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
              {message.sender === 'assistant' && (
                <button
                  className="mt-2 p-1 hover:bg-gray-200 rounded opacity-70 hover:opacity-100"
                  onClick={() => copyToClipboard(message.id, message.text)}
                  title="Copy message"
                >
                  {copiedId === message.id ? (
                    <Check size={16} className="text-green-600" />
                  ) : (
                    <Copy size={16} />
                  )}
                </button>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message assistant">
            <div className="message-content assistant">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about detection results, recommendations, or how the system works..."
            className="input-field flex-1"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="button button-primary"
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
