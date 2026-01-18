/**
 * Chemical Saver - Validation Utilities
 */

import { VALIDATION_LIMITS } from './constants';

/**
 * Validate a single numeric field
 * @param {string} field - Field name
 * @param {number} value - Value to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateNumericField(field, value) {
  const limits = VALIDATION_LIMITS[field];

  if (limits === undefined) {
    return null; // No validation rules for this field
  }

  if (value === null || value === undefined || value === '') {
    return 'This field is required';
  }

  const numValue = Number(value);

  if (isNaN(numValue)) {
    return 'Must be a valid number';
  }

  if (limits.min !== undefined && numValue < limits.min) {
    return `Must be at least ${limits.min}`;
  }

  if (limits.max !== undefined && numValue > limits.max) {
    return `Must be at most ${limits.max}`;
  }

  return null;
}

/**
 * Validate all settings
 * @param {Object} settings - Settings object to validate
 * @returns {Object} Object with field names as keys and error messages as values
 */
export function validateSettings(settings) {
  const errors = {};

  // Validate target_ppm
  const ppmError = validateNumericField('target_ppm', settings.target_ppm);
  if (ppmError) errors.target_ppm = ppmError;

  // Validate chemical_density
  const densityError = validateNumericField('chemical_density', settings.chemical_density);
  if (densityError) errors.chemical_density = densityError;

  // Validate active_intensity
  const intensityError = validateNumericField('active_intensity', settings.active_intensity);
  if (intensityError) errors.active_intensity = intensityError;

  // Validate cost_per_gallon
  const costError = validateNumericField('cost_per_gallon', settings.cost_per_gallon);
  if (costError) errors.cost_per_gallon = costError;

  // Validate min_pump_rate
  const minRateError = validateNumericField('min_pump_rate', settings.min_pump_rate);
  if (minRateError) errors.min_pump_rate = minRateError;

  // Validate max_pump_rate
  const maxRateError = validateNumericField('max_pump_rate', settings.max_pump_rate);
  if (maxRateError) errors.max_pump_rate = maxRateError;

  // Cross-field validation: min must be less than max
  if (!errors.min_pump_rate && !errors.max_pump_rate) {
    if (Number(settings.min_pump_rate) >= Number(settings.max_pump_rate)) {
      errors.min_pump_rate = 'Minimum must be less than maximum';
      errors.max_pump_rate = 'Maximum must be greater than minimum';
    }
  }

  return errors;
}

/**
 * Check if settings object is complete (has all required fields)
 * @param {Object} settings - Settings object to check
 * @returns {boolean} True if all required fields are present
 */
export function isSettingsComplete(settings) {
  if (!settings) return false;

  const requiredFields = [
    'target_ppm',
    'chemical_density',
    'active_intensity',
    'cost_per_gallon',
    'min_pump_rate',
    'max_pump_rate'
  ];

  return requiredFields.every(field =>
    settings[field] !== null &&
    settings[field] !== undefined &&
    settings[field] !== ''
  );
}

/**
 * Sanitize settings object - ensure all values are proper types
 * @param {Object} settings - Raw settings object
 * @returns {Object} Sanitized settings object
 */
export function sanitizeSettings(settings) {
  return {
    target_ppm: parseInt(settings.target_ppm, 10) || 0,
    chemical_density: parseFloat(settings.chemical_density) || 0,
    active_intensity: parseFloat(settings.active_intensity) || 0,
    cost_per_gallon: parseFloat(settings.cost_per_gallon) || 0,
    min_pump_rate: parseFloat(settings.min_pump_rate) || 0,
    max_pump_rate: parseFloat(settings.max_pump_rate) || 0,
    unit_preference: settings.unit_preference || 'gallons'
  };
}

/**
 * Validate production data record
 * @param {Object} record - Production data record
 * @returns {Object} Validation result { isValid, errors, warnings }
 */
export function validateProductionRecord(record) {
  const errors = [];
  const warnings = [];

  // Check timestamp
  if (!record.timestamp) {
    errors.push('Missing timestamp');
  }

  // Check gross fluid rate
  if (record.gross_fluid_rate === null || record.gross_fluid_rate === undefined) {
    warnings.push('Missing gross_fluid_rate - assuming 0');
  } else if (record.gross_fluid_rate < 0) {
    errors.push('Invalid gross_fluid_rate - cannot be negative');
  }

  // Check water cut
  if (record.water_cut !== null && record.water_cut !== undefined) {
    if (record.water_cut < 0 || record.water_cut > 100) {
      warnings.push('water_cut out of range (0-100) - will use last valid value');
    }
  }

  // Check injection rate
  if (record.current_injection_rate < 0) {
    errors.push('Invalid current_injection_rate - cannot be negative');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}
