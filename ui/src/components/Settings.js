import React, { useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  InputAdornment,
  Divider,
  Snackbar,
  Alert,
  CircularProgress
} from '@corva/ui/components';
import SaveIcon from '@material-ui/icons/Save';
import RestoreIcon from '@material-ui/icons/Restore';
import { DEFAULT_SETTINGS, UNIT_CONVERSIONS } from '../utils/constants';
import { validateSettings } from '../utils/validators';
import '../styles/Settings.css';

/**
 * Settings Component - Tab 2
 *
 * Configuration form for well-specific chemical dosage settings.
 * Allows users to input static parameters used in optimization calculations.
 */
function Settings({ settings, loading, error, onSettingsChange, onSave }) {
  const [localSettings, setLocalSettings] = useState(settings);
  const [unitPreference, setUnitPreference] = useState(settings.unit_preference || 'gallons');
  const [validationErrors, setValidationErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [hasChanges, setHasChanges] = useState(false);

  // Handle input change
  const handleChange = useCallback((field, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [field]: value
    }));
    setHasChanges(true);

    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [validationErrors]);

  // Handle unit preference change
  const handleUnitChange = useCallback((event) => {
    const newUnit = event.target.value;
    const oldUnit = unitPreference;

    setUnitPreference(newUnit);

    // Convert values if switching units
    if (newUnit !== oldUnit) {
      const conversionFactor = newUnit === 'liters'
        ? UNIT_CONVERSIONS.GALLONS_TO_LITERS
        : UNIT_CONVERSIONS.LITERS_TO_GALLONS;

      setLocalSettings(prev => ({
        ...prev,
        min_pump_rate: prev.min_pump_rate * conversionFactor,
        max_pump_rate: prev.max_pump_rate * conversionFactor,
        unit_preference: newUnit
      }));
      setHasChanges(true);
    }
  }, [unitPreference]);

  // Handle save
  const handleSave = useCallback(async () => {
    // Validate settings
    const errors = validateSettings(localSettings);
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      setSnackbar({
        open: true,
        message: 'Please fix validation errors before saving',
        severity: 'error'
      });
      return;
    }

    setSaving(true);
    try {
      // Convert back to gallons if in liters mode for storage
      let settingsToSave = { ...localSettings };
      if (unitPreference === 'liters') {
        settingsToSave = {
          ...settingsToSave,
          min_pump_rate: localSettings.min_pump_rate * UNIT_CONVERSIONS.LITERS_TO_GALLONS,
          max_pump_rate: localSettings.max_pump_rate * UNIT_CONVERSIONS.LITERS_TO_GALLONS,
          unit_preference: unitPreference
        };
      }

      const result = await onSave(settingsToSave);

      if (result.success) {
        setSnackbar({
          open: true,
          message: 'Settings saved successfully!',
          severity: 'success'
        });
        setHasChanges(false);
        onSettingsChange(settingsToSave);
      } else {
        throw new Error(result.error || 'Failed to save settings');
      }
    } catch (err) {
      setSnackbar({
        open: true,
        message: err.message || 'Failed to save settings',
        severity: 'error'
      });
    } finally {
      setSaving(false);
    }
  }, [localSettings, unitPreference, onSave, onSettingsChange]);

  // Handle reset to defaults
  const handleReset = useCallback(() => {
    setLocalSettings(DEFAULT_SETTINGS);
    setUnitPreference('gallons');
    setValidationErrors({});
    setHasChanges(true);
  }, []);

  // Close snackbar
  const handleSnackbarClose = useCallback(() => {
    setSnackbar(prev => ({ ...prev, open: false }));
  }, []);

  // Get unit label
  const getVolumeUnit = () => unitPreference === 'liters' ? 'LPD' : 'GPD';
  const getVolumeUnitFull = () => unitPreference === 'liters' ? 'Liters' : 'Gallons';

  if (loading) {
    return (
      <Box className="settings-loading">
        <CircularProgress />
        <Typography variant="body1" style={{ marginTop: 16 }}>
          Loading settings...
        </Typography>
      </Box>
    );
  }

  return (
    <Box className="settings-container">
      <Typography variant="h5" className="settings-title">
        Well Configuration Settings
      </Typography>
      <Typography variant="body2" color="textSecondary" className="settings-subtitle">
        Configure the parameters used for chemical dosage optimization calculations.
      </Typography>

      {/* Chemical Properties Section */}
      <Card className="settings-card">
        <CardContent>
          <Typography variant="h6" className="section-title">
            Chemical Properties
          </Typography>
          <Divider className="section-divider" />

          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Target PPM"
                type="number"
                value={localSettings.target_ppm}
                onChange={(e) => handleChange('target_ppm', parseInt(e.target.value) || 0)}
                error={!!validationErrors.target_ppm}
                helperText={validationErrors.target_ppm || 'Required chemical concentration in water phase'}
                fullWidth
                InputProps={{
                  endAdornment: <InputAdornment position="end">PPM</InputAdornment>
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Chemical Density"
                type="number"
                value={localSettings.chemical_density}
                onChange={(e) => handleChange('chemical_density', parseFloat(e.target.value) || 0)}
                error={!!validationErrors.chemical_density}
                helperText={validationErrors.chemical_density || 'Density for mass-to-volume conversion'}
                fullWidth
                inputProps={{ step: 0.1 }}
                InputProps={{
                  endAdornment: <InputAdornment position="end">kg/L</InputAdornment>
                }}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Typography gutterBottom>
                Active Intensity: {localSettings.active_intensity}%
              </Typography>
              <Slider
                value={localSettings.active_intensity}
                onChange={(e, value) => handleChange('active_intensity', value)}
                min={1}
                max={100}
                step={1}
                marks={[
                  { value: 25, label: '25%' },
                  { value: 50, label: '50%' },
                  { value: 75, label: '75%' },
                  { value: 100, label: '100%' }
                ]}
                valueLabelDisplay="auto"
              />
              <Typography variant="caption" color="textSecondary">
                Percentage of active ingredient in chemical drum
              </Typography>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Cost Per Gallon"
                type="number"
                value={localSettings.cost_per_gallon}
                onChange={(e) => handleChange('cost_per_gallon', parseFloat(e.target.value) || 0)}
                error={!!validationErrors.cost_per_gallon}
                helperText={validationErrors.cost_per_gallon || 'Cost of chemical in USD'}
                fullWidth
                inputProps={{ step: 0.01 }}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  endAdornment: <InputAdornment position="end">/gal</InputAdornment>
                }}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Pump Constraints Section */}
      <Card className="settings-card">
        <CardContent>
          <Typography variant="h6" className="section-title">
            Pump Constraints
          </Typography>
          <Divider className="section-divider" />

          <Grid container spacing={3}>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth>
                <InputLabel>Unit Preference</InputLabel>
                <Select
                  value={unitPreference}
                  onChange={handleUnitChange}
                  label="Unit Preference"
                >
                  <MenuItem value="gallons">Gallons (GPD)</MenuItem>
                  <MenuItem value="liters">Liters (LPD)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                label="Minimum Pump Rate"
                type="number"
                value={localSettings.min_pump_rate}
                onChange={(e) => handleChange('min_pump_rate', parseFloat(e.target.value) || 0)}
                error={!!validationErrors.min_pump_rate}
                helperText={validationErrors.min_pump_rate || 'Physical minimum pump limit'}
                fullWidth
                inputProps={{ step: 0.1 }}
                InputProps={{
                  endAdornment: <InputAdornment position="end">{getVolumeUnit()}</InputAdornment>
                }}
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                label="Maximum Pump Rate"
                type="number"
                value={localSettings.max_pump_rate}
                onChange={(e) => handleChange('max_pump_rate', parseFloat(e.target.value) || 0)}
                error={!!validationErrors.max_pump_rate}
                helperText={validationErrors.max_pump_rate || 'Physical maximum pump limit'}
                fullWidth
                inputProps={{ step: 0.1 }}
                InputProps={{
                  endAdornment: <InputAdornment position="end">{getVolumeUnit()}</InputAdornment>
                }}
              />
            </Grid>
          </Grid>

          <Box className="pump-rate-info" mt={2}>
            <Typography variant="body2" color="textSecondary">
              The optimization will never recommend rates outside these physical pump limits.
              Currently set for {localSettings.min_pump_rate.toFixed(1)} - {localSettings.max_pump_rate.toFixed(1)} {getVolumeUnitFull()} Per Day.
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Box className="settings-actions">
        <Button
          variant="outlined"
          color="secondary"
          startIcon={<RestoreIcon />}
          onClick={handleReset}
          disabled={saving}
        >
          Reset to Defaults
        </Button>

        <Button
          variant="contained"
          color="primary"
          startIcon={saving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
          onClick={handleSave}
          disabled={saving || !hasChanges}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>

      {/* Current Settings Summary */}
      <Card className="settings-summary-card">
        <CardContent>
          <Typography variant="subtitle2" color="textSecondary">
            Current Configuration Summary
          </Typography>
          <Box className="settings-summary" mt={1}>
            <Typography variant="body2">
              <strong>Target:</strong> {localSettings.target_ppm} PPM |
              <strong> Density:</strong> {localSettings.chemical_density} kg/L |
              <strong> Intensity:</strong> {localSettings.active_intensity}% |
              <strong> Cost:</strong> ${localSettings.cost_per_gallon}/gal
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleSnackbarClose} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Settings;
