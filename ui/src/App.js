import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, Tab, Box } from '@corva/ui/components';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import { useCorvaData, useCorvaSettings } from './hooks/useCorvaData';
import { DEFAULT_SETTINGS } from './utils/constants';
import './styles/App.css';

/**
 * Chemical Saver - Main Application Component
 *
 * Dosage optimization app for Corva Dev Center that calculates optimal
 * chemical injection rates and visualizes financial savings.
 */
function App({ well, appData, onSettingChange }) {
  const [activeTab, setActiveTab] = useState(0);

  // Get asset ID from Corva context
  const assetId = well?.asset_id || well?.id;

  // Fetch optimization results data
  const {
    data: optimizationData,
    loading: dataLoading,
    error: dataError,
    refresh: refreshData
  } = useCorvaData(assetId, 'chemical.optimization.results');

  // Fetch and manage settings
  const {
    settings,
    loading: settingsLoading,
    error: settingsError,
    updateSettings,
    saveSettings
  } = useCorvaSettings(assetId, 'chemical.saver.settings', DEFAULT_SETTINGS);

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refreshData();
    }, 30000);

    return () => clearInterval(interval);
  }, [refreshData]);

  // Handle tab change
  const handleTabChange = useCallback((event, newValue) => {
    setActiveTab(newValue);
  }, []);

  // Handle settings save
  const handleSettingsSave = useCallback(async (newSettings) => {
    try {
      await saveSettings(newSettings);
      // Notify parent component if callback exists
      if (onSettingChange) {
        onSettingChange(newSettings);
      }
      return { success: true };
    } catch (error) {
      console.error('Failed to save settings:', error);
      return { success: false, error: error.message };
    }
  }, [saveSettings, onSettingChange]);

  // Calculate summary metrics from latest data
  const getLatestMetrics = useCallback(() => {
    if (!optimizationData || optimizationData.length === 0) {
      return {
        currentWaste: 0,
        corrosionRisk: 'LOW',
        currentPPM: 0,
        targetPPM: settings.target_ppm,
        status: 'NO_DATA'
      };
    }

    const latest = optimizationData[optimizationData.length - 1];

    // Determine corrosion risk based on under-dosing
    let corrosionRisk = 'LOW';
    if (latest.status_flag === 'UNDER_DOSING') {
      corrosionRisk = 'HIGH';
    } else if (latest.current_ppm < latest.target_ppm * 0.9) {
      corrosionRisk = 'HIGH';
    }

    return {
      currentWaste: latest.savings_opportunity_usd || 0,
      corrosionRisk,
      currentPPM: latest.current_ppm || 0,
      targetPPM: latest.target_ppm || settings.target_ppm,
      status: latest.status_flag || 'NO_DATA',
      recommendedRate: latest.recommended_rate_gpd || 0,
      actualRate: latest.actual_rate_gpd || 0,
      waterBPD: latest.water_bpd || 0
    };
  }, [optimizationData, settings.target_ppm]);

  const metrics = getLatestMetrics();

  return (
    <div className="chemical-saver-app">
      <Box className="app-container">
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          className="app-tabs"
        >
          <Tab label="Dashboard" />
          <Tab label="Settings" />
        </Tabs>

        <Box className="tab-content">
          {activeTab === 0 && (
            <Dashboard
              data={optimizationData}
              metrics={metrics}
              settings={settings}
              loading={dataLoading}
              error={dataError}
              onRefresh={refreshData}
            />
          )}

          {activeTab === 1 && (
            <Settings
              settings={settings}
              loading={settingsLoading}
              error={settingsError}
              onSettingsChange={updateSettings}
              onSave={handleSettingsSave}
            />
          )}
        </Box>
      </Box>
    </div>
  );
}

export default App;
