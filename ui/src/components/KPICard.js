import React from 'react';
import { Card, CardContent, Typography, Box } from '@corva/ui/components';
import '../styles/KPICard.css';

/**
 * KPICard Component
 *
 * Displays a key performance indicator with:
 * - Title
 * - Large value
 * - Subtitle/description
 * - Color-coded status (error, warning, success, info)
 * - Optional icon
 */
function KPICard({ title, value, subtitle, color = 'default', icon }) {
  // Map color to CSS class
  const getColorClass = () => {
    switch (color) {
      case 'error':
        return 'kpi-error';
      case 'warning':
        return 'kpi-warning';
      case 'success':
        return 'kpi-success';
      case 'info':
        return 'kpi-info';
      default:
        return 'kpi-default';
    }
  };

  return (
    <Card className={`kpi-card ${getColorClass()}`}>
      <CardContent className="kpi-content">
        <Box className="kpi-header">
          <Typography variant="subtitle2" className="kpi-title">
            {title}
          </Typography>
          {icon && <span className="kpi-icon">{icon}</span>}
        </Box>

        <Typography variant="h4" className="kpi-value">
          {value}
        </Typography>

        {subtitle && (
          <Typography variant="caption" className="kpi-subtitle">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default KPICard;
