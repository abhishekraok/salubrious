import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { put, post } from '../api/client';
import type { UserSettings, UserProfile } from '../types';

export function SettingsPage() {
  const { data: settings, refetch: refetchSettings } = useApi<UserSettings>('/settings');
  const { data: user } = useApi<UserProfile>('/user');
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<string | null>(null);

  if (!settings || !user) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const updateSetting = async (key: string, value: unknown) => {
    await put('/settings', { [key]: value });
    refetchSettings();
  };

  const refreshPrices = async () => {
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const result = await post<{ status: string; updated?: number }>('/prices/refresh');
      setRefreshResult(`${result.status}: ${result.updated ?? 0} holdings updated`);
    } catch {
      setRefreshResult('Failed to refresh prices');
    }
    setRefreshing(false);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Settings</h2>

      {/* User */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Profile</h3>
        <div className="text-sm">
          <span className="text-calm-muted">Name:</span>
          <span className="ml-2 font-medium">{user.name}</span>
          <span className="text-calm-muted ml-4">Currency:</span>
          <span className="ml-2 font-medium">{user.currency}</span>
        </div>
      </Card>

      {/* Behavioral */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Behavioral Guardrails</h3>
        <div className="space-y-4">
          <label className="flex items-center justify-between">
            <span className="text-sm">Hide performance by default</span>
            <input type="checkbox" checked={settings.hide_performance}
              onChange={(e) => updateSetting('hide_performance', e.target.checked)} />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-sm">Require journal entry for manual override</span>
            <input type="checkbox" checked={settings.require_journal_for_override}
              onChange={(e) => updateSetting('require_journal_for_override', e.target.checked)} />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-sm">Enable 24h cooling-off period</span>
            <input type="checkbox" checked={settings.cooldown_enabled}
              onChange={(e) => updateSetting('cooldown_enabled', e.target.checked)} />
          </label>
          <div className="flex items-center justify-between">
            <span className="text-sm">Show values as</span>
            <select value={settings.show_values_mode}
              onChange={(e) => updateSetting('show_values_mode', e.target.value)}
              className="px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface">
              <option value="both">Dollars & Percentages</option>
              <option value="dollars">Dollars only</option>
              <option value="percent">Percentages only</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Prices */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Market Data</h3>
        <div className="flex items-center gap-4">
          <Button variant="secondary" onClick={refreshPrices} disabled={refreshing}>
            {refreshing ? 'Refreshing...' : 'Refresh Prices'}
          </Button>
          {refreshResult && <span className="text-sm text-calm-muted">{refreshResult}</span>}
        </div>
        <p className="text-xs text-calm-muted mt-2">
          Fetches latest closing prices from Yahoo Finance for all holdings.
        </p>
      </Card>
    </div>
  );
}
