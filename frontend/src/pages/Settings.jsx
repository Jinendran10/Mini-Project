import React, { useState } from 'react';
import { Save, AlertCircle } from 'lucide-react';

export default function Settings() {
  const [settings, setSettings] = useState({
    apiUrl: 'http://localhost:8000',
    apiKey: localStorage.getItem('apiKey') || '',
    jieWeight: 0.6,
    rlodWeight: 0.4,
    suspicionThreshold: 0.33,
    poisoningThreshold: 0.67,
    refreshInterval: 5,
    autoRefresh: true,
    darkMode: false,
    notifications: true,
  });

  const [saved, setSaved] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings({
      ...settings,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) : value,
    });
  };

  const handleSave = () => {
    localStorage.setItem('apiKey', settings.apiKey);
    localStorage.setItem('settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="w-full h-full overflow-auto" style={{ background: 'linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%)' }}>
      {/* Header */}
      <div className="border-b border-primary/30 p-6 sticky top-0 z-10" style={{ background: 'linear-gradient(135deg, rgba(131, 56, 236, 0.1) 0%, rgba(10, 10, 15, 0.95) 100%)', backdropFilter: 'blur(10px)' }}>
        <h1 className="text-4xl font-bold text-white gta-glow mb-2">⚙️ Settings</h1>
        <p className="text-gray-300">Configure system preferences and API settings</p>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto p-8">
        {/* Success Message */}
        {saved && (
          <div className="mb-8 bg-accent/10 border-2 border-accent/40 rounded-lg p-4 text-accent flex items-center gap-3">
            <span className="text-xl">✓</span>
            <span className="font-medium">Settings saved successfully</span>
          </div>
        )}

        {/* API Settings */}
        <div className="card mb-8">
          <h2 className="text-2xl font-bold text-white mb-6 gta-glow">API Configuration</h2>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                API URL
              </label>
              <input
                type="text"
                name="apiUrl"
                value={settings.apiUrl}
                onChange={handleChange}
                className="input-field"
                placeholder="http://localhost:8000"
              />
              <p className="text-xs text-gray-400 mt-2">
                Backend API endpoint URL
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                API Key
              </label>
              <input
                type="password"
                name="apiKey"
                value={settings.apiKey}
                onChange={handleChange}
                className="input-field"
                placeholder="Enter your API key"
              />
              <p className="text-xs text-gray-500 mt-1">
                Keep this secret and don't share it
              </p>
            </div>
          </div>
        </div>

        {/* Detection Settings */}
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Detection Settings</h2>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                JIE Weight
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  name="jieWeight"
                  value={settings.jieWeight}
                  onChange={handleChange}
                  min="0"
                  max="1"
                  step="0.05"
                  className="flex-1"
                />
                <span className="text-lg font-bold text-blue-600 w-12">
                  {(settings.jieWeight * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                RLOD Weight
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  name="rlodWeight"
                  value={settings.rlodWeight}
                  onChange={handleChange}
                  min="0"
                  max="1"
                  step="0.05"
                  className="flex-1"
                />
                <span className="text-lg font-bold text-purple-600 w-12">
                  {(settings.rlodWeight * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-blue-50 rounded-lg text-blue-900 text-sm flex gap-2 mb-6">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            <span>
              Total weight: {((settings.jieWeight + settings.rlodWeight) * 100).toFixed(0)}%
              {Math.abs(settings.jieWeight + settings.rlodWeight - 1) > 0.01 && (
                <span className="block mt-1 font-bold">⚠ Weights should sum to 100%</span>
              )}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Suspicion Threshold
              </label>
              <input
                type="number"
                name="suspicionThreshold"
                value={settings.suspicionThreshold}
                onChange={handleChange}
                min="0"
                max="1"
                step="0.05"
                className="input-field"
              />
              <p className="text-xs text-gray-500 mt-1">
                Score range: 0 - {settings.poisoningThreshold}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Poisoning Threshold
              </label>
              <input
                type="number"
                name="poisoningThreshold"
                value={settings.poisoningThreshold}
                onChange={handleChange}
                min="0"
                max="1"
                step="0.05"
                className="input-field"
              />
              <p className="text-xs text-gray-500 mt-1">
                Score range: {settings.suspicionThreshold} - 1.0
              </p>
            </div>
          </div>
        </div>

        {/* UI Settings */}
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">User Interface</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Auto-refresh Interval (seconds)
              </label>
              <input
                type="number"
                name="refreshInterval"
                value={settings.refreshInterval}
                onChange={handleChange}
                min="1"
                max="60"
                className="input-field"
              />
            </div>

            <div className="flex items-center justify-between py-3 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-700">
                Auto-refresh Dashboard
              </label>
              <input
                type="checkbox"
                name="autoRefresh"
                checked={settings.autoRefresh}
                onChange={handleChange}
                className="w-5 h-5"
              />
            </div>

            <div className="flex items-center justify-between py-3 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-700">
                Dark Mode
              </label>
              <input
                type="checkbox"
                name="darkMode"
                checked={settings.darkMode}
                onChange={handleChange}
                className="w-5 h-5"
              />
            </div>

            <div className="flex items-center justify-between py-3 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-700">
                Enable Notifications
              </label>
              <input
                type="checkbox"
                name="notifications"
                checked={settings.notifications}
                onChange={handleChange}
                className="w-5 h-5"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-3">
          <button className="button button-secondary">
            Reset to Defaults
          </button>
          <button onClick={handleSave} className="button button-primary flex items-center gap-2">
            <Save size={20} />
            Save Settings
          </button>
        </div>

        {/* Info Section */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-bold text-blue-900 mb-2">💡 Pro Tips</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Adjust weights based on your model's characteristics</li>
            <li>• Increase refresh interval for large datasets</li>
            <li>• Set thresholds to match your risk tolerance</li>
            <li>• Enable notifications for high-risk detection events</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
