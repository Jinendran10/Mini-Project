import React, { useState, useEffect } from 'react';
import { LineChart, BarChart, PieChart, RadarChart } from '../components/Charts';
import MetricCard from '../components/MetricCard';
import { RefreshCw, Download } from 'lucide-react';

export default function Dashboard() {
  const [detectionData, setDetectionData] = useState({
    jieScores: [],
    rlodScores: [],
    combinedScores: [],
    labels: [],
  });
  const [stats, setStats] = useState({
    avgJieScore: 0.32,
    avgRlodScore: 0.38,
    avgCombinedScore: 0.34,
    suspiciousSamples: 12,
    cleanSamples: 988,
    poisoningRate: 1.2,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Simulate loading detection data
    generateMockData();
  }, []);

  const generateMockData = () => {
    setIsLoading(true);
    setTimeout(() => {
      const labels = Array.from({ length: 50 }, (_, i) => `Batch ${i + 1}`);
      const jieScores = labels.map(() => Math.random() * 0.5);
      const rlodScores = labels.map(() => Math.random() * 0.6);
      const combinedScores = labels.map((_, i) => jieScores[i] * 0.6 + rlodScores[i] * 0.4);

      setDetectionData({
        jieScores,
        rlodScores,
        combinedScores,
        labels,
      });
      setIsLoading(false);
    }, 500);
  };

  const lineChartData = {
    labels: detectionData.labels,
    datasets: [
      {
        label: 'JIE Score',
        data: detectionData.jieScores,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
      },
      {
        label: 'RLOD Score',
        data: detectionData.rlodScores,
        borderColor: '#ec4899',
        backgroundColor: 'rgba(236, 72, 153, 0.1)',
        tension: 0.4,
      },
    ],
  };

  const combinedChartData = {
    labels: detectionData.labels,
    datasets: [
      {
        label: 'Combined Score (60% JIE + 40% RLOD)',
        data: detectionData.combinedScores,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const scoreDistributionData = {
    labels: ['Clean (0-0.33)', 'Suspicious (0.33-0.67)', 'Poisoned (0.67-1.0)'],
    datasets: [
      {
        data: [
          detectionData.combinedScores.filter((s) => s < 0.33).length,
          detectionData.combinedScores.filter((s) => s >= 0.33 && s < 0.67).length,
          detectionData.combinedScores.filter((s) => s >= 0.67).length,
        ],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
      },
    ],
  };

  const methodComparisonData = {
    labels: ['Accuracy', 'Speed', 'Robustness', 'Scalability', 'False Positive Rate'],
    datasets: [
      {
        label: 'JIE',
        data: [0.92, 0.75, 0.88, 0.80, 0.15],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
      },
      {
        label: 'RLOD',
        data: [0.85, 0.88, 0.92, 0.85, 0.18],
        borderColor: '#ec4899',
        backgroundColor: 'rgba(236, 72, 153, 0.1)',
      },
      {
        label: 'Combined',
        data: [0.94, 0.82, 0.95, 0.82, 0.12],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
      },
    ],
  };

  const getScoreStatus = (score) => {
    if (score < 0.33) return { status: 'success', label: 'Clean' };
    if (score < 0.67) return { status: 'warning', label: 'Suspicious' };
    return { status: 'danger', label: 'Poisoned' };
  };

  const avgCombined = detectionData.combinedScores.length > 0
    ? detectionData.combinedScores.reduce((a, b) => a + b, 0) / detectionData.combinedScores.length
    : 0;

  const combinedStatus = getScoreStatus(avgCombined);

  return (
    <div className="w-full h-full overflow-auto" style={{ background: 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%)' }}>
      {/* Header */}
      <div className="border-b border-primary/30 p-6 sticky top-0 z-10" style={{ background: 'linear-gradient(135deg, rgba(131, 56, 236, 0.1) 0%, rgba(10, 10, 15, 0.95) 100%)', backdropFilter: 'blur(10px)' }}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold text-white gta-glow mb-2">📊 Detection Dashboard</h1>
            <p className="text-gray-300">Real-time poisoning detection analytics</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={generateMockData}
              disabled={isLoading}
              className="button button-primary flex items-center gap-2 min-w-[120px] justify-center"
            >
              <RefreshCw size={20} className={isLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button className="button button-secondary flex items-center gap-2 min-w-[120px] justify-center">
              <Download size={20} />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-8">
        {/* KPI Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-10">
          <MetricCard
            title="Avg JIE Score"
            value={stats.avgJieScore}
            status="normal"
          />
          <MetricCard
            title="Avg RLOD Score"
            value={stats.avgRlodScore}
            status="normal"
          />
          <MetricCard
            title="Combined Score"
            value={avgCombined}
            status={combinedStatus.status}
          />
          <MetricCard
            title="Suspicious Samples"
            value={stats.suspiciousSamples}
            status="warning"
          />
          <MetricCard
            title="Clean Samples"
            value={stats.cleanSamples}
            status="success"
          />
          <MetricCard
            title="Poisoning Rate"
            value={stats.poisoningRate}
            unit="%"
            status={stats.poisoningRate > 1 ? 'warning' : 'success'}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
          <LineChart title="Detection Scores Over Time" data={lineChartData} />
          <LineChart title="Combined Detection Score Trend" data={combinedChartData} />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
          <PieChart title="Score Distribution" data={scoreDistributionData} />
          <RadarChart title="Method Comparison" data={methodComparisonData} />
        </div>

        {/* Detection Summary Table */}
        <div className="card">
          <h3 className="card-header">Recent Detections</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">Sample ID</th>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">JIE Score</th>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">RLOD Score</th>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">Combined</th>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">Status</th>
                  <th className="px-6 py-3 text-left text-gray-700 font-semibold">Mitigation Weight</th>
                </tr>
              </thead>
              <tbody>
                {detectionData.combinedScores.slice(0, 10).map((score, idx) => {
                  const jieScore = detectionData.jieScores[idx];
                  const rlodScore = detectionData.rlodScores[idx];
                  const status = getScoreStatus(score);
                  const mitigationWeight = Math.max(0, Math.min(1, score * 1.2));

                  return (
                    <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                      <td className="px-6 py-3 text-gray-900 font-medium">Sample-{String(idx + 1).padStart(3, '0')}</td>
                      <td className="px-6 py-3 text-gray-700">{jieScore.toFixed(3)}</td>
                      <td className="px-6 py-3 text-gray-700">{rlodScore.toFixed(3)}</td>
                      <td className="px-6 py-3 text-gray-900 font-medium">{score.toFixed(3)}</td>
                      <td className="px-6 py-3">
                        <span
                          className={`score-badge score-${status.status}`}
                        >
                          {status.label}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-gray-700">{mitigationWeight.toFixed(3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
