import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { formatNumber } from '../utils/formatters';
import '../styles/Chart.css';

/**
 * DualLineChart Component
 *
 * Displays a time series chart with two lines:
 * - Line A (Red): Actual Injection Rate
 * - Line B (Green): Recommended Injection Rate
 *
 * Visual Goal: Show the gap between Red and Green closing over time.
 */
function DualLineChart({ data, height = 350, showLegend = true }) {
  // Format timestamp for X-axis
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format date for tooltip
  const formatDateTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Calculate Y-axis domain
  const yDomain = useMemo(() => {
    if (!data || data.length === 0) return [0, 10];

    const allValues = data.flatMap(d => [d.actualRate, d.recommendedRate]).filter(v => v != null);
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);

    // Add 10% padding
    const padding = (max - min) * 0.1 || 1;
    return [Math.max(0, min - padding), max + padding];
  }, [data]);

  // Calculate average recommended rate for reference line
  const avgRecommended = useMemo(() => {
    if (!data || data.length === 0) return null;
    const validRates = data.filter(d => d.recommendedRate != null).map(d => d.recommendedRate);
    if (validRates.length === 0) return null;
    return validRates.reduce((a, b) => a + b, 0) / validRates.length;
  }, [data]);

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;

    const dataPoint = payload[0]?.payload;

    return (
      <div className="chart-tooltip">
        <p className="tooltip-time">{formatDateTime(label)}</p>
        <div className="tooltip-content">
          <div className="tooltip-row actual">
            <span className="tooltip-label">Actual:</span>
            <span className="tooltip-value">{formatNumber(dataPoint?.actualRate, 2)} GPD</span>
          </div>
          <div className="tooltip-row recommended">
            <span className="tooltip-label">Recommended:</span>
            <span className="tooltip-value">{formatNumber(dataPoint?.recommendedRate, 2)} GPD</span>
          </div>
          {dataPoint?.actualRate != null && dataPoint?.recommendedRate != null && (
            <div className="tooltip-row difference">
              <span className="tooltip-label">Difference:</span>
              <span className={`tooltip-value ${dataPoint.actualRate > dataPoint.recommendedRate ? 'over' : 'under'}`}>
                {dataPoint.actualRate > dataPoint.recommendedRate ? '+' : ''}
                {formatNumber(dataPoint.actualRate - dataPoint.recommendedRate, 2)} GPD
              </span>
            </div>
          )}
          {dataPoint?.status && (
            <div className="tooltip-status">
              Status: <span className={`status-${dataPoint.status.toLowerCase()}`}>{dataPoint.status}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Custom legend component
  const renderLegend = (props) => {
    const { payload } = props;

    return (
      <div className="chart-legend">
        {payload.map((entry, index) => (
          <span key={`legend-${index}`} className="legend-item">
            <span
              className="legend-color"
              style={{ backgroundColor: entry.color }}
            />
            <span className="legend-label">{entry.value}</span>
          </span>
        ))}
        <span className="legend-hint">
          (Closing the gap = Saving money)
        </span>
      </div>
    );
  };

  if (!data || data.length === 0) {
    return (
      <div className="chart-empty">
        <p>No data available for chart</p>
      </div>
    );
  }

  return (
    <div className="dual-line-chart">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />

          <XAxis
            dataKey="timestamp"
            tickFormatter={formatTime}
            stroke="#666"
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
          />

          <YAxis
            domain={yDomain}
            tickFormatter={(value) => formatNumber(value, 1)}
            stroke="#666"
            tick={{ fontSize: 12 }}
            label={{
              value: 'Injection Rate (GPD)',
              angle: -90,
              position: 'insideLeft',
              style: { textAnchor: 'middle', fill: '#666', fontSize: 12 }
            }}
          />

          <Tooltip content={<CustomTooltip />} />

          {showLegend && (
            <Legend content={renderLegend} verticalAlign="top" height={36} />
          )}

          {/* Reference line for average recommended rate */}
          {avgRecommended && (
            <ReferenceLine
              y={avgRecommended}
              stroke="#4caf50"
              strokeDasharray="5 5"
              strokeWidth={1}
              label={{
                value: `Avg: ${formatNumber(avgRecommended, 1)}`,
                fill: '#4caf50',
                fontSize: 10,
                position: 'right'
              }}
            />
          )}

          {/* Actual Injection Rate - Red Line */}
          <Line
            type="monotone"
            dataKey="actualRate"
            name="Actual Rate"
            stroke="#f44336"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: '#f44336' }}
            connectNulls
          />

          {/* Recommended Injection Rate - Green Line */}
          <Line
            type="monotone"
            dataKey="recommendedRate"
            name="Recommended Rate"
            stroke="#4caf50"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, fill: '#4caf50' }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DualLineChart;
