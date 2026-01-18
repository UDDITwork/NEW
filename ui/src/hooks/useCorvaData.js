/**
 * Chemical Saver - Custom Hooks for Corva Data
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { DEFAULT_SETTINGS, REFRESH_INTERVALS } from '../utils/constants';

/**
 * Hook for fetching time-series data from Corva
 * @param {number} assetId - The well/asset ID
 * @param {string} collection - The collection name to query
 * @param {Object} options - Additional options (limit, timeRange, etc.)
 * @returns {Object} { data, loading, error, refresh }
 */
export function useCorvaData(assetId, collection, options = {}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { limit = 100, timeRange = 24 * 60 * 60 } = options; // Default 24 hours

  const fetchData = useCallback(async () => {
    if (!assetId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Calculate time range
      const endTime = Math.floor(Date.now() / 1000);
      const startTime = endTime - timeRange;

      // Corva API call - this would be the actual SDK call in production
      // For now, we simulate the API structure
      const response = await fetchCorvaDataset({
        provider: 'custom',
        collection,
        assetId,
        query: {
          timestamp: { $gte: startTime, $lte: endTime }
        },
        sort: { timestamp: 1 },
        limit
      });

      setData(response || []);
    } catch (err) {
      console.error(`Error fetching ${collection}:`, err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [assetId, collection, limit, timeRange]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
}

/**
 * Hook for managing well settings from Corva
 * @param {number} assetId - The well/asset ID
 * @param {string} collection - The settings collection name
 * @param {Object} defaultSettings - Default settings to use if none found
 * @returns {Object} { settings, loading, error, updateSettings, saveSettings }
 */
export function useCorvaSettings(assetId, collection, defaultSettings = DEFAULT_SETTINGS) {
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDirty, setIsDirty] = useState(false);

  // Fetch settings on mount
  useEffect(() => {
    async function loadSettings() {
      if (!assetId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await fetchCorvaDataset({
          provider: 'custom',
          collection,
          assetId,
          limit: 1
        });

        if (response && response.length > 0) {
          // Merge with defaults to ensure all fields exist
          setSettings({ ...defaultSettings, ...response[0] });
        } else {
          // Use defaults if no settings found
          setSettings(defaultSettings);
        }
      } catch (err) {
        console.error('Error loading settings:', err);
        setError(err);
        setSettings(defaultSettings);
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, [assetId, collection, defaultSettings]);

  // Update settings locally
  const updateSettings = useCallback((newSettings) => {
    setSettings(prev => ({
      ...prev,
      ...newSettings
    }));
    setIsDirty(true);
  }, []);

  // Save settings to Corva
  const saveSettings = useCallback(async (settingsToSave) => {
    if (!assetId) {
      throw new Error('No asset ID provided');
    }

    try {
      setLoading(true);
      setError(null);

      const dataToSave = {
        ...settingsToSave,
        asset_id: assetId,
        updated_at: new Date().toISOString()
      };

      await postCorvaDataset({
        provider: 'custom',
        collection,
        assetId,
        data: [dataToSave]
      });

      setSettings(dataToSave);
      setIsDirty(false);

      return { success: true };
    } catch (err) {
      console.error('Error saving settings:', err);
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [assetId, collection]);

  return { settings, loading, error, isDirty, updateSettings, saveSettings };
}

/**
 * Hook for real-time data subscription
 * @param {number} assetId - The well/asset ID
 * @param {string} collection - The collection to subscribe to
 * @param {Function} onData - Callback when new data arrives
 * @returns {Object} { connected, lastUpdate }
 */
export function useCorvaSubscription(assetId, collection, onData) {
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const subscriptionRef = useRef(null);

  useEffect(() => {
    if (!assetId || !onData) return;

    // In production, this would use Corva's real-time subscription
    // For now, we poll at regular intervals
    const pollInterval = setInterval(async () => {
      try {
        const latestData = await fetchCorvaDataset({
          provider: 'custom',
          collection,
          assetId,
          sort: { timestamp: -1 },
          limit: 1
        });

        if (latestData && latestData.length > 0) {
          const newData = latestData[0];
          setLastUpdate(newData.timestamp);
          onData(newData);
        }

        setConnected(true);
      } catch (err) {
        console.error('Subscription error:', err);
        setConnected(false);
      }
    }, REFRESH_INTERVALS.data);

    subscriptionRef.current = pollInterval;

    return () => {
      if (subscriptionRef.current) {
        clearInterval(subscriptionRef.current);
      }
    };
  }, [assetId, collection, onData]);

  return { connected, lastUpdate };
}

// =============================================================================
// Corva API Helpers (would be replaced by actual SDK in production)
// =============================================================================

/**
 * Fetch data from Corva dataset
 * In production, this uses the Corva SDK
 */
async function fetchCorvaDataset({ provider, collection, assetId, query, sort, limit }) {
  // Check if Corva SDK is available (global object injected by Corva platform)
  if (window.corva && window.corva.api) {
    try {
      return await window.corva.api.getDataset(provider, collection, {
        asset_id: assetId,
        query,
        sort,
        limit
      });
    } catch (err) {
      console.error('Corva SDK error:', err);
      throw err;
    }
  }

  // Fallback for development/testing - return mock data
  console.warn('Corva SDK not available, using mock data');
  return getMockData(collection, limit);
}

/**
 * Post data to Corva dataset
 * In production, this uses the Corva SDK
 */
async function postCorvaDataset({ provider, collection, assetId, data }) {
  if (window.corva && window.corva.api) {
    try {
      return await window.corva.api.postDataset(provider, collection, assetId, data);
    } catch (err) {
      console.error('Corva SDK error:', err);
      throw err;
    }
  }

  // Fallback for development - simulate success
  console.warn('Corva SDK not available, simulating save');
  return { success: true };
}

/**
 * Generate mock data for development
 */
function getMockData(collection, limit = 100) {
  if (collection.includes('settings')) {
    return [DEFAULT_SETTINGS];
  }

  // Generate mock optimization results
  const now = Math.floor(Date.now() / 1000);
  const data = [];

  for (let i = 0; i < limit; i++) {
    const timestamp = now - (limit - i) * 60; // 1 minute intervals
    const recommended = 3 + Math.random() * 2; // 3-5 GPD
    const actual = recommended + (Math.random() - 0.3) * 2; // Slight variance

    data.push({
      timestamp,
      recommended_rate_gpd: recommended,
      actual_rate_gpd: actual,
      savings_opportunity_usd: (actual - recommended) * 25,
      status_flag: actual > recommended * 1.1 ? 'OVER_DOSING' :
                   actual < recommended * 0.9 ? 'UNDER_DOSING' : 'OPTIMAL',
      water_bpd: 500 + Math.random() * 200,
      current_ppm: 180 + Math.random() * 40,
      target_ppm: 200
    });
  }

  return data;
}
