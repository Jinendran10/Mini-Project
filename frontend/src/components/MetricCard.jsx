import React from 'react';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

export default function MetricCard({ title, value, unit = '', icon: Icon = null, trend = null, status = 'normal' }) {
  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'border-l-green-500';
      case 'warning':
        return 'border-l-yellow-500';
      case 'danger':
        return 'border-l-red-500';
      default:
        return 'border-l-blue-500';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="text-green-500" size={24} />;
      case 'warning':
        return <AlertCircle className="text-yellow-500" size={24} />;
      case 'danger':
        return <AlertCircle className="text-red-500" size={24} />;
      default:
        return <Clock className="text-blue-500" size={24} />;
    }
  };

  return (
    <div className={`metric-card ${getStatusColor()}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="metric-label mb-2">{title}</p>
          <p className="metric-value flex items-baseline">
            <span>{typeof value === 'number' ? value.toFixed(2) : value}</span>
            {unit && <span className="text-base ml-1 opacity-80">{unit}</span>}
          </p>
          {trend && (
            <p className={`text-xs mt-2 ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last check
            </p>
          )}
        </div>
        <div>{getStatusIcon()}</div>
      </div>
    </div>
  );
}
