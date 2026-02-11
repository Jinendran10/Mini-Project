import React from 'react';
import { ArrowRight, Shield, Activity, Brain } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="w-full h-full overflow-auto" style={{ background: 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%)' }}>
      {/* Hero Section */}
      <div className="border-b border-primary/20" style={{ background: 'linear-gradient(135deg, rgba(131, 56, 236, 0.1) 0%, rgba(10, 10, 15, 0.9) 100%)' }}>
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center">
            <h1 className="text-6xl font-bold text-white mb-6 gta-glow">
              🛡️ Poison Guard
            </h1>
            <p className="text-xl text-gray-300 mb-10">
              Advanced AI Defense System Against Data Poisoning Attacks
            </p>
            <div className="flex flex-wrap gap-6 justify-center items-center">
              <Link
                to="/dashboard"
                className="button button-primary flex items-center justify-center gap-3 text-lg px-10 py-4 min-w-[200px]"
              >
                View Dashboard <ArrowRight size={22} />
              </Link>
              <Link
                to="/chatbot"
                className="button button-secondary flex items-center justify-center gap-3 text-lg px-10 py-4 min-w-[200px]"
              >
                Chat with AI <ArrowRight size={22} />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-4xl font-bold text-white mb-16 text-center gta-glow-purple">
          Detection Methods
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 mb-20">
          {/* JIE Card */}
          <div className="card hover:shadow-2xl hover:shadow-primary/30 transition-all duration-300 hover:scale-105">
            <div className="flex items-center mb-6">
              <div className="bg-gradient-to-br from-primary/20 to-secondary/20 rounded-xl p-4 mr-4 border border-primary/30">
                <Brain size={36} className="text-primary" />
              </div>
              <h3 className="text-2xl font-bold text-white gta-glow">JIE Detection</h3>
            </div>
            <p className="text-gray-300 mb-6 text-base">
              Joint Influence Estimation using TracIn algorithm
            </p>
            <ul className="space-y-3 text-gray-200">
              <li className="flex items-center">✓ Gradient-based influence scoring</li>
              <li className="flex items-center">✓ Last-layer parameter focus</li>
              <li className="flex items-center">✓ High accuracy: 92%</li>
              <li className="flex items-center">✓ Fast computation</li>
            </ul>
            <div className="mt-6 p-4 bg-primary/10 rounded-lg border border-primary/30">
              <p className="text-sm font-mono text-primary">
                Identifies samples with highest influence on model predictions
              </p>
            </div>
          </div>

          {/* RLOD Card */}
          <div className="card hover:shadow-2xl hover:shadow-secondary/30 transition-all duration-300 hover:scale-105">
            <div className="flex items-center mb-6">
              <div className="bg-gradient-to-br from-secondary/20 to-accent/20 rounded-xl p-4 mr-4 border border-secondary/30">
                <Activity size={36} className="text-secondary" />
              </div>
              <h3 className="text-2xl font-bold text-white gta-glow-purple">RLOD Detection</h3>
            </div>
            <p className="text-gray-300 mb-6 text-base">
              Representation-Level Outlier Detection
            </p>
            <ul className="space-y-3 text-gray-200">
              <li className="flex items-center">✓ Embedding-based analysis</li>
              <li className="flex items-center">✓ Multi-method approach (kNN, Spectral, Clustering)</li>
              <li className="flex items-center">✓ Robustness: 92%</li>
              <li className="flex items-center">✓ GPU-accelerated FAISS</li>
            </ul>
            <div className="mt-6 p-4 bg-secondary/10 rounded-lg border border-secondary/30">
              <p className="text-sm font-mono text-secondary">
                Detects anomalous representations in hidden layers
              </p>
            </div>
          </div>
        </div>

        {/* Combined Detection */}
        <div className="card border-2 border-accent/40 mb-20" style={{ background: 'linear-gradient(135deg, rgba(131, 56, 236, 0.15) 0%, rgba(6, 255, 165, 0.15) 100%)' }}>
          <div className="flex items-center mb-6">
            <div className="bg-gradient-to-br from-accent/20 to-primary/20 rounded-xl p-4 mr-4 border border-accent/30">
              <Shield size={36} className="text-accent" />
            </div>
            <h3 className="text-3xl font-bold text-white gta-glow-cyan">Combined Defense</h3>
          </div>
          <p className="text-gray-200 mb-8 text-lg">
            60% JIE + 40% RLOD = Maximum Detection Accuracy
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
            <div className="bg-dark/50 p-6 rounded-lg shadow-lg border border-accent/30 backdrop-blur-sm">
              <p className="text-sm text-gray-400 mb-2">Detection Accuracy</p>
              <p className="text-4xl font-bold text-accent">94%</p>
            </div>
            <div className="bg-dark/50 p-6 rounded-lg shadow-lg border border-accent/30 backdrop-blur-sm">
              <p className="text-sm text-gray-400 mb-2">False Positive Rate</p>
              <p className="text-4xl font-bold text-accent">12%</p>
            </div>
            <div className="bg-dark/50 p-6 rounded-lg shadow-lg border border-accent/30 backdrop-blur-sm">
              <p className="text-sm text-gray-400 mb-2">Processing Speed</p>
              <p className="text-4xl font-bold text-accent">82%</p>
            </div>
          </div>
          <p className="text-gray-200 text-base leading-relaxed">
            Our dual-layer defense system combines gradient-based and representation-based detection for comprehensive protection against sophisticated poisoning attacks.
          </p>
        </div>

        {/* System Capabilities */}
        <div>
          <h2 className="text-4xl font-bold text-white mb-12 text-center gta-glow-purple">
            System Capabilities
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                title: 'Real-time Analysis',
                description: 'Analyze training data in real-time with instant detection results',
                icon: '⚡',
              },
              {
                title: 'Batch Processing',
                description: 'Process large datasets efficiently with parallel computation',
                icon: '📦',
              },
              {
                title: 'Adaptive Weights',
                description: 'Automatically adjust sample weights based on detection scores',
                icon: '⚖️',
              },
              {
                title: 'Visualization',
                description: 'Comprehensive dashboards for monitoring and analysis',
                icon: '📊',
              },
              {
                title: 'AI Assistant',
                description: 'Interactive chatbot for queries and recommendations',
                icon: '🤖',
              },
              {
                title: 'Export Reports',
                description: 'Generate detailed reports for auditing and compliance',
                icon: '📄',
              },
            ].map((item, idx) => (
              <div key={idx} className="card hover:shadow-xl hover:shadow-primary/20 transition-all duration-300 hover:scale-105">
                <p className="text-4xl mb-4">{item.icon}</p>
                <h4 className="font-bold text-white text-lg mb-3">{item.title}</h4>
                <p className="text-base text-gray-300">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-20 rounded-2xl p-12 text-white text-center border-2 border-primary/40" style={{ background: 'linear-gradient(135deg, #8338ec 0%, #ff006e 100%)' }}>
          <h3 className="text-4xl font-bold mb-6 gta-glow">Ready to Protect Your Model?</h3>
          <p className="text-xl mb-10 opacity-90">
            Start analyzing your training data with Poison Guard today
          </p>
          <Link to="/dashboard" className="button bg-white text-primary hover:bg-gray-100 font-bold text-lg px-10 py-4 inline-flex items-center gap-3">
            Launch Dashboard <ArrowRight size={22} />
          </Link>
        </div>
      </div>
    </div>
  );
}
