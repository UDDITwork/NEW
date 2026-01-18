import React from 'react';
import { Box, Typography, Chip } from '@corva/ui/components';
import '../styles/StatusIndicator.css';

/**
 * StatusIndicator Component
 *
 * Displays the current dosing status with visual indicators:
 * - OPTIMAL: Green - Operating at recommended rate
 * - OVER_DOSING: Red - Injecting more than needed (wasting money)
 * - UNDER_DOSING: Orange - Injecting less than needed (corrosion risk)
 * - PUMP_OFF: Gray - Well not producing
 * - ERROR: Red outline - Data error detected
 * - NO_DATA: Gray outline - No recent data
 */
function StatusIndicator({ status }) {
  // Status configuration
  const statusConfig = {
    OPTIMAL: {
      label: 'Optimal',
      description: 'Chemical injection is at the recommended rate',
      color: 'success',
      icon: '✓',
      className: 'status-optimal'
    },
    OVER_DOSING: {
      label: 'Over-Dosing',
      description: 'Injecting more chemical than needed - potential savings available',
      color: 'error',
      icon: '↑',
      className: 'status-over'
    },
    UNDER_DOSING: {
      label: 'Under-Dosing',
      description: 'Injecting less chemical than needed - corrosion risk!',
      color: 'warning',
      icon: '↓',
      className: 'status-under'
    },
    PUMP_OFF: {
      label: 'Pump Off',
      description: 'Well is not currently producing',
      color: 'default',
      icon: '⏸',
      className: 'status-off'
    },
    ERROR: {
      label: 'Error',
      description: 'Data quality issue detected - check sensors',
      color: 'error',
      icon: '!',
      className: 'status-error'
    },
    NO_DATA: {
      label: 'No Data',
      description: 'No recent data received from the well',
      color: 'default',
      icon: '?',
      className: 'status-nodata'
    }
  };

  const config = statusConfig[status] || statusConfig.NO_DATA;

  return (
    <Box className={`status-indicator ${config.className}`}>
      <Box className="status-content">
        <Box className="status-main">
          <span className="status-icon">{config.icon}</span>
          <Chip
            label={config.label}
            color={config.color}
            className="status-chip"
            size="medium"
          />
        </Box>
        <Typography variant="body2" className="status-description">
          {config.description}
        </Typography>
      </Box>

      {/* Visual pulse for active states */}
      {(status === 'OVER_DOSING' || status === 'UNDER_DOSING') && (
        <Box className="status-pulse" />
      )}
    </Box>
  );
}

export default StatusIndicator;
