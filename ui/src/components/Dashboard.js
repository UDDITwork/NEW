import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  IconButton,
  Tooltip
} from '@corva/ui/components';
import RefreshIcon from '@material-ui/icons/Refresh';
import DualLineChart from './DualLineChart';
import KPICard from './KPICard';
import StatusIndicator from './StatusIndicator';
import { formatCurrency, formatNumber } from '../utils/formatters';
import '../styles/Dashboard.css';

/**
 * Dashboard Component - Tab 1
 *
 * Displays real-time optimization data with:
 * - KPI Cards (Current Waste, Corrosion Risk, Current PPM)
 * - Time Series Chart (Actual vs Recommended Injection Rate)
 * - Status Indicators
 */
function Dashboard({ data, metrics, settings, loading, error, onRefresh }) {
  // Process chart data
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map(record => ({
      timestamp: record.timestamp * 1000, // Convert to milliseconds for JS Date
      actualRate: record.actual_rate_gpd || 0,
      recommendedRate: record.recommended_rate_gpd || 0,
      status: record.status_flag
    })).sort((a, b) => a.timestamp - b.timestamp);
  }, [data]);

  // Calculate cumulative savings
  const cumulativeSavings = useMemo(() => {
    if (!data || data.length === 0) return 0;

    return data.reduce((total, record) => {
      // Only count positive savings (over-dosing scenarios)
      const savings = record.savings_opportunity_usd || 0;
      return total + (savings > 0 ? savings : 0);
    }, 0);
  }, [data]);

  // Determine waste display color
  const getWasteColor = (waste) => {
    if (waste > 0) return 'error'; // Over-dosing - Red
    if (waste < 0) return 'warning'; // Under-dosing - Orange
    return 'success'; // Optimal - Green
  };

  // Determine corrosion risk color
  const getCorrosionColor = (risk) => {
    return risk === 'HIGH' ? 'error' : 'success';
  };

  if (loading && (!data || data.length === 0)) {
    return (
      <Box className="dashboard-loading">
        <CircularProgress />
        <Typography variant="body1" style={{ marginTop: 16 }}>
          Loading optimization data...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="dashboard-error">
        <Typography variant="h6" color="error">
          Error Loading Data
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {error.message || 'Unable to fetch optimization data'}
        </Typography>
        <IconButton onClick={onRefresh} color="primary" style={{ marginTop: 16 }}>
          <RefreshIcon />
        </IconButton>
      </Box>
    );
  }

  return (
    <Box className="dashboard-container">
      {/* Header with Refresh Button */}
      <Box className="dashboard-header">
        <Typography variant="h5" className="dashboard-title">
          Chemical Dosage Optimization
        </Typography>
        <Tooltip title="Refresh Data">
          <IconButton onClick={onRefresh} disabled={loading}>
            <RefreshIcon className={loading ? 'spinning' : ''} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* KPI Cards Row */}
      <Grid container spacing={3} className="kpi-row">
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Current Waste"
            value={formatCurrency(Math.abs(metrics.currentWaste))}
            subtitle={metrics.currentWaste > 0 ? 'per day (over-dosing)' : 'per day'}
            color={getWasteColor(metrics.currentWaste)}
            icon={metrics.currentWaste > 0 ? '💸' : '✓'}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Corrosion Risk"
            value={metrics.corrosionRisk}
            subtitle={metrics.corrosionRisk === 'HIGH' ? 'Under-dosing detected' : 'Adequate protection'}
            color={getCorrosionColor(metrics.corrosionRisk)}
            icon={metrics.corrosionRisk === 'HIGH' ? '⚠️' : '🛡️'}
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Current PPM"
            value={formatNumber(metrics.currentPPM, 0)}
            subtitle={`Target: ${metrics.targetPPM} PPM`}
            color={
              Math.abs(metrics.currentPPM - metrics.targetPPM) / metrics.targetPPM < 0.1
                ? 'success'
                : 'warning'
            }
            icon="🧪"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Cumulative Savings"
            value={formatCurrency(cumulativeSavings)}
            subtitle="Total savings opportunity"
            color="info"
            icon="📊"
          />
        </Grid>
      </Grid>

      {/* Status Indicator */}
      <Box className="status-section">
        <StatusIndicator status={metrics.status} />
      </Box>

      {/* Main Chart */}
      <Card className="chart-card">
        <CardContent>
          <Typography variant="h6" className="chart-title">
            Injection Rate Comparison
          </Typography>
          <Typography variant="body2" color="textSecondary" className="chart-subtitle">
            Actual (Red) vs Recommended (Green) - Close the gap to save money
          </Typography>

          <Box className="chart-container">
            {chartData.length > 0 ? (
              <DualLineChart
                data={chartData}
                height={350}
                showLegend={true}
              />
            ) : (
              <Box className="no-data-message">
                <Typography variant="body1" color="textSecondary">
                  No optimization data available yet.
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Data will appear once the backend processes production streams.
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Current Values Summary */}
      <Grid container spacing={3} className="summary-row">
        <Grid item xs={12} sm={6} md={4}>
          <Card className="summary-card">
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Recommended Rate
              </Typography>
              <Typography variant="h4" className="summary-value">
                {formatNumber(metrics.recommendedRate, 2)} <span className="unit">GPD</span>
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card className="summary-card">
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Actual Rate
              </Typography>
              <Typography variant="h4" className="summary-value">
                {formatNumber(metrics.actualRate, 2)} <span className="unit">GPD</span>
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card className="summary-card">
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Water Production
              </Typography>
              <Typography variant="h4" className="summary-value">
                {formatNumber(metrics.waterBPD, 0)} <span className="unit">BPD</span>
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;
