import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import DeveloperPanel from './DeveloperPanel';
import { chatOnce } from './api';

function ModeToggle({ mode, setMode }) {
  return (
    <div className="inline-flex rounded-xl border border-white/10 bg-dark/60 p-1">
      <button
        type="button"
        onClick={() => setMode('user')}
        className={`px-3 py-1.5 text-xs font-semibold rounded-lg ${mode === 'user' ? 'bg-white/10 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
      >
        User Mode
      </button>
      <button
        type="button"
        onClick={() => setMode('dev')}
        className={`px-3 py-1.5 text-xs font-semibold rounded-lg ${mode === 'dev' ? 'bg-white/10 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
      >
        Developer Mode
      </button>
    </div>
  );
}

function Bubble({ role, children }) {
  const isUser = role === 'user';
  return (
    <div className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={
          `max-w-[min(720px,92%)] rounded-2xl px-4 py-3 text-sm leading-6 ` +
          (isUser
            ? 'bg-secondary/30 border border-secondary/30 text-gray-100'
            : 'bg-white/5 border border-white/10 text-gray-100')
        }
      >
        <div className="whitespace-pre-wrap break-words">{children}</div>
      </div>
    </div>
  );
}

function TypingLine({ text = 'Generating…' }) {
  return (
    <div className="text-xs text-gray-500 px-1">{text}</div>
  );
}

export default function ChatGPTInterface() {
  const [mode, setMode] = useState('user');
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'How can I help? Your message is scanned by JIE + RLOD in the background.',
      detection: null,
      rawResult: null,
      streaming: false,
    },
  ]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);

  const listRef = useRef(null);
  const streamTimerRef = useRef(null);

  const latestChatResult = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].rawResult) return messages[i].rawResult;
    }
    return null;
  }, [messages]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => () => {
    if (streamTimerRef.current) window.clearInterval(streamTimerRef.current);
  }, []);

  const streamIntoMessage = (messageId, fullText) => {
    if (streamTimerRef.current) window.clearInterval(streamTimerRef.current);
    let idx = 0;
    streamTimerRef.current = window.setInterval(() => {
      idx += 2;
      setMessages((prev) => prev.map((m) => (
        m.id === messageId
          ? { ...m, content: fullText.slice(0, idx) }
          : m
      )));
      if (idx >= fullText.length) {
        window.clearInterval(streamTimerRef.current);
        streamTimerRef.current = null;
      }
    }, 12);
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || sending) return;

    setSending(true);
    setDraft('');

    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      detection: null,
      rawResult: null,
      streaming: false,
    };

    const assistantId = `a-${Date.now() + 1}`;
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      detection: null,
      rawResult: null,
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    try {
      const data = await chatOnce(text);

      streamIntoMessage(assistantId, data.response || '');

      setMessages((prev) => prev.map((m) => (
        m.id === assistantId
          ? {
            ...m,
            rawResult: data,
            detection: {
              chunks: data.chunks,
              poisoned_count: data.poisoned_count,
              clean_count: data.clean_count,
              processing_ms: data.processing_ms,
            },
            streaming: false,
          }
          : m
      )));
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error';
      setMessages((prev) => prev.map((m) => (
        m.id === assistantId
          ? {
            ...m,
            content:
              `Error: ${detail}\n\n` +
              `Make sure the backend is running (example):\n` +
              `python -m uvicorn src.api.main:app --port 8000`,
            streaming: false,
          }
          : m
      )));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-screen bg-dark text-gray-100">
      <div className={`h-full ${mode === 'dev' ? 'md:flex' : ''}`}>
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/10 bg-darker/70 backdrop-blur">
            <div className="text-sm font-semibold tracking-wide">Poison Guard</div>
            <ModeToggle mode={mode} setMode={setMode} />
          </div>

          <div className="flex-1 overflow-hidden">
            <div className={`h-full mx-auto w-full ${mode === 'dev' ? 'max-w-4xl' : 'max-w-3xl'} flex flex-col`}>
              <div ref={listRef} className="flex-1 overflow-auto px-4 py-6 space-y-4">
                {messages.map((m) => (
                  <Bubble key={m.id} role={m.role}>
                    {m.content}
                    {m.streaming && <div className="mt-2"><TypingLine /></div>}
                  </Bubble>
                ))}
              </div>

              <div className="px-4 pb-5">
                <div className="rounded-2xl border border-white/10 bg-darker/60 backdrop-blur p-2">
                  <div className="flex items-end gap-2">
                    <textarea
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          send();
                        }
                      }}
                      rows={2}
                      placeholder="Message Poison Guard…"
                      className="flex-1 resize-none bg-transparent outline-none px-3 py-2 text-sm text-gray-100 placeholder:text-gray-500"
                      disabled={sending}
                    />
                    <button
                      type="button"
                      onClick={send}
                      disabled={sending || !draft.trim()}
                      className="shrink-0 h-10 w-10 rounded-xl bg-primary/90 hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                      title="Send"
                    >
                      <Send size={18} />
                    </button>
                  </div>
                  <div className="px-3 pb-1 text-[11px] text-gray-600">
                    Shift+Enter for newline · backend: /api/chat · scoring: JIE + RLOD
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {mode === 'dev' && (
          <DeveloperPanel latestChatResult={latestChatResult} />
        )}
      </div>
    </div>
  );
}
