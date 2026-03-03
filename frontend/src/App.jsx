import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatGPT from './pages/ChatGPT';
import './App.css';

// Catch render errors so one broken page doesn't blank the whole app
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, color: '#f87171', fontFamily: 'monospace' }}>
          <h2>⚠ Page render error</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{this.state.error.message}</pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 16, padding: '8px 16px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<ChatGPT />} />
          <Route path="*" element={<ChatGPT />} />
        </Routes>
      </ErrorBoundary>
    </Router>
  );
}

export default App;
