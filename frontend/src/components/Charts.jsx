import React from 'react';
import { Line, Bar, Pie, Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  RadarController,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,   // ← required for Radar charts
  RadarController,
  Filler,
  Tooltip,
  Legend
);

export function LineChart({ title, data, options = {} }) {
  return (
    <div className="chart-container">
      <h3 className="card-header">{title}</h3>
      <Line
        data={data}
        options={{
          responsive: true,
          plugins: {
            legend: {
              position: 'top',
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 1,
            },
          },
          ...options,
        }}
      />
    </div>
  );
}

export function BarChart({ title, data, options = {} }) {
  return (
    <div className="chart-container">
      <h3 className="card-header">{title}</h3>
      <Bar
        data={data}
        options={{
          responsive: true,
          plugins: {
            legend: {
              position: 'top',
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 1,
            },
          },
          ...options,
        }}
      />
    </div>
  );
}

export function PieChart({ title, data, options = {} }) {
  return (
    <div className="chart-container">
      <h3 className="card-header">{title}</h3>
      <div style={{ position: 'relative', width: '100%', height: '300px' }}>
        <Pie
          data={data}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'right',
              },
            },
            ...options,
          }}
        />
      </div>
    </div>
  );
}

export function RadarChart({ title, data, options = {} }) {
  return (
    <div className="chart-container">
      <h3 className="card-header">{title}</h3>
      <Radar
        data={data}
        options={{
          responsive: true,
          plugins: {
            legend: {
              position: 'top',
            },
          },
          scales: {
            r: {
              beginAtZero: true,
              max: 1,
            },
          },
          ...options,
        }}
      />
    </div>
  );
}
