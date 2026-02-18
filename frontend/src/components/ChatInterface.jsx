import React, { useState, useRef, useEffect } from 'react';
import {
  Send, ChevronRight, ChevronDown, ShieldCheck, ShieldAlert,
  AlertTriangle, Copy, Check, Info,
} from 'lucide-react';
import axios from 'axios';

// â”€â”€ API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

async function sendChat(message) {
  const res = await axios.post(
    `${API_URL}/api/chat`,
    { message },
    { headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' } },
  );
  return res.data;
}

// â”€â”€ score helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function scoreColor(score) {
  if (score >= 0.7) return '#f87171';   // red   â€“ poisoned
  if (score >= 0.4) return '#fbbf24';   // amber â€“ suspicious
  return '#4ade80';                      // green â€“ clean
}
function scoreLabel(score) {
  if (score >= 0.7) return 'Poisoned';
  if (score >= 0.4) return 'Suspicious';
  return 'Clean';
}
function ScorePill({ score }) {
  if (score == null) return <span style={{ color: '#6b7280', fontSize: 11 }}>N/A</span>;
  return (
    <span style={{
      background: scoreColor(score) + '22',
      color: scoreColor(score),
      border: `1px solid ${scoreColor(score)}55`,
      borderRadius: 4, padding: '1px 6px', fontSize: 11, fontWeight: 700,
    }}>
      {scoreLabel(score)} {(score * 100).toFixed(0)}%
    </span>
  );
}

// â”€â”€ detection panel (shown per-message) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function DetectionPanel({ chunks, poisonedCount, cleanCount, processingMs }) {
  const [open, setOpen] = useState(false);
  const [expandedChunk, setExpandedChunk] = useState(null);

  if (!chunks || chunks.length === 0) return null;

  return (
    <div style={{
      marginTop: 8, borderRadius: 8,
      border: '1px solid rgba(255,255,255,0.1)',
      background: 'rgba(255,255,255,0.03)',
      fontSize: 12,
    }}>
      {/* Toggle header */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px', background: 'transparent', border: 'none',
          cursor: 'pointer', color: '#9ca3af', textAlign: 'left',
        }}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {poisonedCount > 0
          ? <ShieldAlert size={14} style={{ color: '#f87171' }} />
          : <ShieldCheck size={14} style={{ color: '#4ade80' }} />}
        <span style={{ color: poisonedCount > 0 ? '#f87171' : '#4ade80', fontWeight: 600 }}>
          {poisonedCount > 0
            ? `⚠ Input flagged as potentially poisoned`
            : `✓ Input scan: clean`}
        </span>
        <span style={{ marginLeft: 'auto', color: '#6b7280' }}>input scanned · {processingMs}ms</span>
      </button>

      {/* Expanded: per-chunk table */}
      {open && (
        <div style={{ padding: '0 12px 12px' }}>
          {/* Summary bar */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 8, color: '#9ca3af' }}>
            <span>🟢 JIE+RLOD input scan</span>
            {poisonedCount > 0
              ? <span style={{ color: '#f87171' }}>🔴 Flagged as poisoned</span>
              : <span style={{ color: '#4ade80' }}>✓ No poison trigger detected</span>}
          </div>

          {chunks.map(chunk => (
            <div key={chunk.sample_id} style={{
              marginBottom: 6, borderRadius: 6,
              border: `1px solid ${chunk.is_poisoned ? '#f8717155' : 'rgba(255,255,255,0.07)'}`,
              background: chunk.is_poisoned ? 'rgba(248,113,113,0.05)' : 'rgba(255,255,255,0.02)',
              overflow: 'hidden',
            }}>
              {/* Chunk header row */}
              <div
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 10px', cursor: 'pointer',
                }}
                onClick={() => setExpandedChunk(expandedChunk === chunk.sample_id ? null : chunk.sample_id)}
              >
                <span style={{ color: '#9ca3af', fontFamily: 'monospace', fontSize: 10 }}>
                  Your input
                </span>
                {chunk.is_poisoned && (
                  <span style={{ color: '#f87171', fontSize: 10, fontWeight: 700, marginLeft: 2 }}>
                    ⚠ FLAGGED
                  </span>
                )}
                <span style={{ flex: 1, color: '#d1d5db', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {chunk.text.slice(0, 80)}{chunk.text.length > 80 ? 'â€¦' : ''}
                </span>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <ScorePill score={chunk.combined_score} />
                </div>
              </div>

              {/* Expanded chunk detail */}
              {expandedChunk === chunk.sample_id && (
                <div style={{ padding: '6px 10px 10px', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                  <p style={{ color: '#e5e7eb', marginBottom: 8 }}>{chunk.text}</p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 }}>
                    {[
                      ['JIE Score', chunk.jie_score],
                      ['RLOD Score', chunk.rlod_score],
                      ['Combined', chunk.combined_score],
                      ['Mitigation wt.', chunk.mitigation_weight],
                    ].map(([label, val]) => (
                      <div key={label} style={{
                        background: 'rgba(255,255,255,0.04)', borderRadius: 4, padding: '6px 8px',
                      }}>
                        <div style={{ color: '#6b7280', fontSize: 10, marginBottom: 2 }}>{label}</div>
                        <div style={{ color: '#e5e7eb', fontWeight: 700 }}>
                          {val != null ? `${(val * 100).toFixed(1)}%` : 'â€”'}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ marginTop: 6, color: '#6b7280', fontSize: 10 }}>
                    Scanned by JIE + RLOD before model generation
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// â”€â”€ message bubble â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Message({ msg, onCopy, copied }) {
  const isUser = msg.role === 'user';

  return (
    <div style={{
      display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 16, animation: 'fadeIn 0.2s ease',
    }}>
      {/* avatar */}
      {!isUser && (
        <div style={{
          width: 32, height: 32, borderRadius: '50%', flexShrink: 0, marginRight: 10,
          background: 'linear-gradient(135deg,#7c3aed,#ec4899)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, marginTop: 2,
        }}>ðŸ›¡ï¸</div>
      )}

      <div style={{ maxWidth: '72%', minWidth: 60 }}>
        {/* bubble */}
        <div style={{
          padding: '12px 16px', borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          background: isUser
            ? 'linear-gradient(135deg,#7c3aed,#6d28d9)'
            : 'rgba(255,255,255,0.07)',
          color: '#f3f4f6', fontSize: 14, lineHeight: 1.6,
          border: isUser ? 'none' : '1px solid rgba(255,255,255,0.1)',
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          position: 'relative',
        }}>
          {msg.content}

          {/* copy button */}
          {!isUser && (
            <button
              onClick={() => onCopy(msg.id, msg.content)}
              title="Copy"
              style={{
                position: 'absolute', top: 8, right: 8,
                background: 'transparent', border: 'none', cursor: 'pointer',
                color: '#6b7280', padding: 2,
              }}
            >
              {copied === msg.id ? <Check size={13} style={{ color: '#4ade80' }} /> : <Copy size={13} />}
            </button>
          )}
        </div>

        {/* detection panel below assistant message */}
        {!isUser && msg.detection && (
          <DetectionPanel
            chunks={msg.detection.chunks}
            poisonedCount={msg.detection.poisoned_count}
            cleanCount={msg.detection.clean_count}
            processingMs={msg.detection.processing_ms}
          />
        )}

        <div style={{ fontSize: 10, color: '#4b5563', marginTop: 4, textAlign: isUser ? 'right' : 'left' }}>
          {msg.time}
        </div>
      </div>

      {isUser && (
        <div style={{
          width: 32, height: 32, borderRadius: '50%', flexShrink: 0, marginLeft: 10,
          background: 'rgba(255,255,255,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, marginTop: 2,
        }}>ðŸ‘¤</div>
      )}
    </div>
  );
}

// â”€â”€ typing indicator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function TypingIndicator({ stage }) {
  const stages = {
    scanning:  '🔍 Scanning input with JIE + RLOD…',
    detecting: '🧬 Running combined poison detection…',
    generating: '✏️ Generating response…',
  };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
        background: 'linear-gradient(135deg,#7c3aed,#ec4899)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
      }}>ðŸ›¡ï¸</div>
      <div style={{
        padding: '10px 16px', borderRadius: '18px 18px 18px 4px',
        background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)',
        color: '#9ca3af', fontSize: 13,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span>{stages[stage] || stages.scanning}</span>
        <span style={{ display: 'flex', gap: 4 }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 6, height: 6, background: '#7c3aed', borderRadius: '50%',
              animation: 'bounce 1.2s infinite', animationDelay: `${i * 0.2}s`,
              display: 'inline-block',
            }} />
          ))}
        </span>
      </div>
    </div>
  );
}

// â”€â”€ main component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 0, role: 'assistant',
      content:
        'Hi! I\'m Poison Guard — powered by your fine-tuned model.\n\n' +
        'Every message you send goes through two steps:\n' +
        '1️⃣  JIE + RLOD scan your input for backdoor / poison triggers\n' +
        '2️⃣  The fine-tuned model generates a response\n\n' +
        'Click the shield row below any of my replies to inspect the detection scores.',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      detection: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('scanning');
  const [copied, setCopied] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = {
      id: Date.now(), role: 'user', content: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Simulate visible pipeline stages
    const stageTimeline = [
      ['scanning',    500],
      ['detecting',  1000],
      ['generating',    0],
    ];
    let delay = 0;
    for (const [s, ms] of stageTimeline) {
      delay += ms;
      setTimeout(() => setStage(s), delay);
    }

    try {
      const data = await sendChat(text);
      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        detection: {
          chunks:         data.chunks,
          poisoned_count: data.poisoned_count,
          clean_count:    data.clean_count,
          processing_ms:  data.processing_ms,
        },
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: `âŒ Error: ${err.response?.data?.detail || err.message}\n\nMake sure the backend is running:\nD:/Mini-Project/scripts/.venv/Scripts/python.exe -m uvicorn src.api.main:app --port 8000`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          detection: null,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const suggestions = [
    'What is data poisoning?',
    'How does JIE detection work?',
    'Explain RLOD and embedding outliers',
    'What is the combined detection score?',
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%)',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(10,10,15,0.95)', backdropFilter: 'blur(10px)',
        display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: '50%',
          background: 'linear-gradient(135deg,#7c3aed,#ec4899)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
        }}>ðŸ›¡ï¸</div>
        <div>
          <h2 style={{ color: '#f3f4f6', margin: 0, fontSize: 17, fontWeight: 700 }}>Poison Guard AI</h2>
          <p style={{ color: '#6b7280', margin: 0, fontSize: 12 }}>RAG Â· JIE + RLOD detection Â· Fine-tuned GPT-2</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80', display: 'inline-block' }} />
          <span style={{ color: '#4ade80', fontSize: 12 }}>Online</span>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
        {/* Suggestions (shown when only the welcome message exists) */}
        {messages.length === 1 && !loading && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
            {suggestions.map(s => (
              <button
                key={s}
                onClick={() => { setInput(s); inputRef.current?.focus(); }}
                style={{
                  padding: '8px 14px', borderRadius: 20, fontSize: 13,
                  background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)',
                  color: '#c4b5fd', cursor: 'pointer',
                }}
              >{s}</button>
            ))}
          </div>
        )}

        {messages.map(msg => (
          <Message key={msg.id} msg={msg} onCopy={handleCopy} copied={copied} />
        ))}

        {loading && <TypingIndicator stage={stage} />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 20px 20px', borderTop: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(10,10,15,0.95)', backdropFilter: 'blur(10px)', flexShrink: 0,
      }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            rows={2}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
            }}
            placeholder="Ask anything — your input is scanned by JIE+RLOD before reaching the model…"
            disabled={loading}
            style={{
              flex: 1, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 12, padding: '12px 14px', color: '#f3f4f6', fontSize: 14,
              resize: 'none', fontFamily: 'inherit', outline: 'none',
            }}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              width: 44, height: 44, borderRadius: 12, flexShrink: 0,
              background: loading || !input.trim()
                ? 'rgba(124,58,237,0.3)'
                : 'linear-gradient(135deg,#7c3aed,#6d28d9)',
              border: 'none', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff',
            }}
          >
            <Send size={18} />
          </button>
        </form>
        <p style={{ color: '#374151', fontSize: 11, margin: '6px 0 0', textAlign: 'center' }}>
          Shift+Enter for newline · detection: JIE + RLOD · model: fine-tuned GPT-2
        </p>
      </div>

      {/* Bounce keyframe injected inline */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
