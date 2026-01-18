/**
 * Chemical Saver - Constants and Configuration
 */

// Default settings for wells without user configuration
export const DEFAULT_SETTINGS = {
  target_ppm: 200,
  chemical_density: 1.0,
  active_intensity: 100,
  cost_per_gallon: 10.0,  // Safe default per requirements
  min_pump_rate: 0.5,
  max_pump_rate: 50.0,
  unit_preference: 'gallons'
};

// Unit conversion factors
export const UNIT_CONVERSIONS = {
  GALLONS_TO_LITERS: 3.78541,
  LITERS_TO_GALLONS: 0.264172,
  BPD_TO_LPD: 158.987,
  LPD_TO_BPD: 0.00629
};

// Status flag definitions
export const STATUS_FLAGS = {
  OPTIMAL: {
    key: 'OPTIMAL',
    label: 'Optimal',
    severity: 'success'
  },
  OVER_DOSING: {
    key: 'OVER_DOSING',
    label: 'Over-Dosing',
    severity: 'error'
  },
  UNDER_DOSING: {
    key: 'UNDER_DOSING',
    label: 'Under-Dosing',
    severity: 'warning'
  },
  PUMP_OFF: {
    key: 'PUMP_OFF',
    label: 'Pump Off',
    severity: 'default'
  },
  ERROR: {
    key: 'ERROR',
    label: 'Error',
    severity: 'error'
  },
  NO_DATA: {
    key: 'NO_DATA',
    label: 'No Data',
    severity: 'default'
  }
};

// Validation limits
export const VALIDATION_LIMITS = {
  target_ppm: { min: 1, max: 10000 },
  chemical_density: { min: 0.1, max: 5.0 },
  active_intensity: { min: 1, max: 100 },
  cost_per_gallon: { min: 0, max: 1000 },
  min_pump_rate: { min: 0, max: 100 },
  max_pump_rate: { min: 0.1, max: 1000 }
};

// Chart colors
export const CHART_COLORS = {
  actual: '#f44336',      // Red
  recommended: '#4caf50', // Green
  optimal: '#2196f3',     // Blue
  warning: '#ff9800',     // Orange
  grid: '#e0e0e0'
};

// Refresh intervals (milliseconds)
export const REFRESH_INTERVALS = {
  data: 30000,     // 30 seconds
  settings: 60000  // 1 minute
};

// Corva collection names
export const COLLECTIONS = {
  SETTINGS: 'chemical.saver.settings',
  RESULTS: 'chemical.optimization.results',
  PRODUCTION: 'production.fluids'
};

// API endpoints (relative to Corva base URL)
export const API_ENDPOINTS = {
  GET_SETTINGS: '/v1/data/custom/chemical.saver.settings/',
  POST_SETTINGS: '/v1/data/custom/chemical.saver.settings/',
  GET_RESULTS: '/v1/data/custom/chemical.optimization.results/'
};

// Error messages
export const ERROR_MESSAGES = {
  LOAD_SETTINGS_FAILED: 'Failed to load well settings',
  SAVE_SETTINGS_FAILED: 'Failed to save settings',
  LOAD_DATA_FAILED: 'Failed to load optimization data',
  INVALID_SETTINGS: 'Please check your settings values',
  NO_ASSET: 'No well selected'
};
