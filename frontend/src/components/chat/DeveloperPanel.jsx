import React, { useMemo, useState } from 'react';
import { chatOnce } from './api';
import { getPrimaryChunk, confidenceLabelFromCombined } from './scoreUtils';

function MetricRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b border-white/5">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-sm text-gray-100 font-semibold text-right">{value}</div>
    </div>
  );
}

function ScoreValue({ value }) {
  if (value == null) return <span className="text-gray-500">—</span>;
  return <span>{(value * 100).toFixed(1)}%</span>;
}

export default function DeveloperPanel({ latestChatResult }) {
  const [injectText, setInjectText] = useState('');
  const [injectLoading, setInjectLoading] = useState(false);
  const [injectResult, setInjectResult] = useState(null);
  const [injectError, setInjectError] = useState(null);

  const latestChunk = useMemo(() => getPrimaryChunk(latestChatResult), [latestChatResult]);
  const injectChunk = useMemo(() => getPrimaryChunk(injectResult), [injectResult]);

  const runInject = async () => {
    const text = injectText.trim();
    if (!text || injectLoading) return;
    setInjectLoading(true);
    setInjectError(null);
    try {
      const data = await chatOnce(text);
      setInjectResult(data);
    } catch (e) {
      setInjectError(e?.response?.data?.detail || e?.message || 'Unknown error');
      setInjectResult(null);
    } finally {
      setInjectLoading(false);
    }
  };

  const beforeCombined = latestChunk?.combined_score ?? null;
  const afterCombined = injectChunk?.combined_score ?? null;

  return (
    <aside className="w-full md:w-[420px] border-l border-white/10 bg-darker/80 backdrop-blur p-4 overflow-auto">
      <div className="space-y-6">
        <section className="space-y-3">
          <div className="text-sm font-semibold text-gray-100">Poison Injection</div>
          <textarea
            value={injectText}
            onChange={(e) => setInjectText(e.target.value)}
            rows={5}
            placeholder="Paste a malicious/poison-like snippet to evaluate (runs existing JIE+RLOD scoring via /api/chat)…"
            className="w-full rounded-xl bg-dark border border-white/10 focus:border-primary/50 focus:ring-0 p-3 text-sm text-gray-100 outline-none resize-none"
          />
          <button
            onClick={runInject}
            disabled={injectLoading || !injectText.trim()}
            className="w-full rounded-xl px-4 py-2 text-sm font-semibold bg-primary/90 hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {injectLoading ? 'Injecting…' : 'Inject & Evaluate'}
          </button>
          {injectError && (
            <div className="text-xs text-danger">Error: {injectError}</div>
          )}
          <div className="text-[11px] text-gray-500">
            This does not modify any dataset or model weights. It only evaluates the text with the existing backend scoring.
          </div>
        </section>

        <section className="space-y-3">
          <div className="text-sm font-semibold text-gray-100">Results</div>

          <div className="rounded-xl border border-white/10 bg-dark/60 p-3">
            <div className="text-xs text-gray-400 mb-2">Latest chat message (silent background scan)</div>
            <MetricRow label="JIE Score (Influence)" value={<ScoreValue value={latestChunk?.jie_score} />} />
            <MetricRow label="RLOD Score" value={<ScoreValue value={latestChunk?.rlod_score} />} />
            <MetricRow label="Combined Score" value={<ScoreValue value={latestChunk?.combined_score} />} />
            <MetricRow label="Poisoned / Clean" value={latestChunk ? (latestChunk.is_poisoned ? 'Poisoned' : 'Clean') : '—'} />
            <MetricRow label="Confidence Level" value={confidenceLabelFromCombined(latestChunk?.combined_score)} />
            <MetricRow label="Mitigation Weight" value={latestChunk?.mitigation_weight != null ? (latestChunk.mitigation_weight).toFixed(4) : '—'} />
            <MetricRow label="Processing (ms)" value={latestChatResult?.processing_ms != null ? latestChatResult.processing_ms : '—'} />
          </div>

          <div className="rounded-xl border border-white/10 bg-dark/60 p-3">
            <div className="text-xs text-gray-400 mb-2">Injected text evaluation</div>
            <MetricRow label="JIE Score (Influence)" value={<ScoreValue value={injectChunk?.jie_score} />} />
            <MetricRow label="RLOD Score" value={<ScoreValue value={injectChunk?.rlod_score} />} />
            <MetricRow label="Combined Score" value={<ScoreValue value={injectChunk?.combined_score} />} />
            <MetricRow label="Poisoned / Clean" value={injectChunk ? (injectChunk.is_poisoned ? 'Poisoned' : 'Clean') : '—'} />
            <MetricRow label="Confidence Level" value={confidenceLabelFromCombined(injectChunk?.combined_score)} />
            <MetricRow label="Mitigation Weight" value={injectChunk?.mitigation_weight != null ? (injectChunk.mitigation_weight).toFixed(4) : '—'} />
            <MetricRow label="Processing (ms)" value={injectResult?.processing_ms != null ? injectResult.processing_ms : '—'} />
          </div>
        </section>

        <section className="space-y-3">
          <div className="text-sm font-semibold text-gray-100">Before/After (Combined)</div>
          <div className="rounded-xl border border-white/10 bg-dark/60 p-3 space-y-3">
            <div>
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>Before (latest chat)</span>
                <span>{beforeCombined != null ? `${(beforeCombined * 100).toFixed(1)}%` : '—'}</span>
              </div>
              <div className="h-2 rounded bg-white/5 overflow-hidden">
                <div
                  className="h-2 bg-accent/80"
                  style={{ width: `${beforeCombined != null ? Math.max(0, Math.min(100, beforeCombined * 100)) : 0}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>After (injected)</span>
                <span>{afterCombined != null ? `${(afterCombined * 100).toFixed(1)}%` : '—'}</span>
              </div>
              <div className="h-2 rounded bg-white/5 overflow-hidden">
                <div
                  className="h-2 bg-primary/80"
                  style={{ width: `${afterCombined != null ? Math.max(0, Math.min(100, afterCombined * 100)) : 0}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-gray-500">
              Bars reflect backend-provided combined scores (no re-scoring in the UI).
            </div>
          </div>
        </section>
      </div>
    </aside>
  );
}
