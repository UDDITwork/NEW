/**
 * Chemical Saver - Formatting Utilities
 */

/**
 * Format a number with specified decimal places
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted number string
 */
export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  return Number(value).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

/**
 * Format a value as currency (USD)
 * @param {number} value - The amount to format
 * @param {boolean} showCents - Whether to show cents (default: true)
 * @returns {string} Formatted currency string
 */
export function formatCurrency(value, showCents = true) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0
  }).format(value);
}

/**
 * Format a percentage value
 * @param {number} value - The percentage value (0-100)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage string
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  return `${formatNumber(value, decimals)}%`;
}

/**
 * Format a Unix timestamp as a readable date/time
 * @param {number} timestamp - Unix timestamp in seconds
 * @param {string} format - Format type: 'full', 'date', 'time', 'short'
 * @returns {string} Formatted date/time string
 */
export function formatTimestamp(timestamp, format = 'full') {
  if (!timestamp) return '--';

  // Handle both seconds and milliseconds
  const ms = timestamp > 1e11 ? timestamp : timestamp * 1000;
  const date = new Date(ms);

  if (isNaN(date.getTime())) return '--';

  switch (format) {
    case 'date':
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });

    case 'time':
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });

    case 'short':
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      });

    case 'full':
    default:
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
  }
}

/**
 * Format a volume value with unit
 * @param {number} value - The volume value
 * @param {string} unit - The unit ('gpd', 'lpd', 'bpd')
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted volume string with unit
 */
export function formatVolume(value, unit = 'gpd', decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  const unitLabels = {
    gpd: 'GPD',
    lpd: 'LPD',
    bpd: 'BPD',
    gpm: 'GPM'
  };

  return `${formatNumber(value, decimals)} ${unitLabels[unit.toLowerCase()] || unit.toUpperCase()}`;
}

/**
 * Format a PPM value
 * @param {number} value - The PPM value
 * @returns {string} Formatted PPM string
 */
export function formatPPM(value) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  return `${formatNumber(value, 0)} PPM`;
}

/**
 * Format a relative time difference
 * @param {number} timestamp - Unix timestamp to compare against now
 * @returns {string} Human-readable time difference
 */
export function formatRelativeTime(timestamp) {
  if (!timestamp) return '--';

  const ms = timestamp > 1e11 ? timestamp : timestamp * 1000;
  const diff = Date.now() - ms;
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * Format a large number with abbreviations (K, M, B)
 * @param {number} value - The number to format
 * @param {number} decimals - Decimal places for abbreviated values
 * @returns {string} Abbreviated number string
 */
export function formatCompact(value, decimals = 1) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }

  const absValue = Math.abs(value);

  if (absValue >= 1e9) {
    return `${formatNumber(value / 1e9, decimals)}B`;
  }
  if (absValue >= 1e6) {
    return `${formatNumber(value / 1e6, decimals)}M`;
  }
  if (absValue >= 1e3) {
    return `${formatNumber(value / 1e3, decimals)}K`;
  }

  return formatNumber(value, decimals);
}
