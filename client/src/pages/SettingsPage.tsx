import { useState, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { put, post } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import type { UserSettings, UserProfile } from '../types';

export function SettingsPage() {
  const { data: settings, refetch: refetchSettings } = useApi<UserSettings>('/settings');
  const { data: user, refetch: refetchUser } = useApi<UserProfile>('/user');
  const { logout } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<string | null>(null);
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [profileCurrency, setProfileCurrency] = useState('');
  const [importResult, setImportResult] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const startEditProfile = () => {
    setProfileName(user.name);
    setProfileCurrency(user.currency);
    setEditingProfile(true);
  };

  const saveProfile = async () => {
    await put('/user', { name: profileName, currency: profileCurrency });
    refetchUser();
    setEditingProfile(false);
  };

  const handleExportProfile = () => {
    const token = localStorage.getItem('salubrious_token');
    fetch('/api/profile/export', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(res => res.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'salubrious-profile.json';
        a.click();
        URL.revokeObjectURL(url);
      });
  };

  const handleImportProfile = async (file: File) => {
    setImporting(true);
    setImportResult(null);
    try {
      const token = localStorage.getItem('salubrious_token');
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/profile/import', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Import failed');
      }
      const result = await res.json();
      const summary = result.imported;
      setImportResult(
        `Imported: ${summary.accounts} accounts, ${summary.holdings} holdings, ${summary.sleeves} sleeves, ${summary.reviews} reviews, ${summary.journal_entries} journal entries`
      );
      refetchUser();
      refetchSettings();
    } catch (err) {
      setImportResult(err instanceof Error ? err.message : 'Import failed');
    }
    setImporting(false);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Settings</h2>

      {/* User */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Profile</h3>
        {editingProfile ? (
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-calm-muted mb-1">Name</label>
              <input
                type="text"
                value={profileName}
                onChange={e => setProfileName(e.target.value)}
                className="px-3 py-2 text-sm border border-calm-border rounded bg-calm-surface w-full max-w-xs"
              />
            </div>
            <div>
              <label className="block text-sm text-calm-muted mb-1">Currency</label>
              <input
                type="text"
                value={profileCurrency}
                onChange={e => setProfileCurrency(e.target.value)}
                maxLength={3}
                className="px-3 py-2 text-sm border border-calm-border rounded bg-calm-surface w-20"
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={saveProfile}>Save</Button>
              <Button variant="secondary" onClick={() => setEditingProfile(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="text-calm-muted">Name:</span>
              <span className="ml-2 font-medium">{user.name}</span>
              <span className="text-calm-muted ml-4">Currency:</span>
              <span className="ml-2 font-medium">{user.currency}</span>
              {user.email && (
                <>
                  <span className="text-calm-muted ml-4">Email:</span>
                  <span className="ml-2 font-medium">{user.email}</span>
                </>
              )}
            </div>
            <Button variant="secondary" onClick={startEditProfile}>Edit</Button>
          </div>
        )}
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

      {/* Data Export/Import */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Data</h3>
        <div className="space-y-4">
          <div>
            <p className="text-sm mb-2">Export a complete backup of your profile including policy, sleeves, accounts, holdings, journals, and reviews.</p>
            <Button variant="secondary" onClick={handleExportProfile}>Export full profile (JSON)</Button>
          </div>
          <div className="border-t border-calm-border pt-4">
            <p className="text-sm mb-2">Import a profile backup. This will <strong>replace all existing data</strong> for your account.</p>
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={importing}>
              {importing ? 'Importing...' : 'Import profile (JSON)'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImportProfile(file);
                e.target.value = '';
              }}
            />
          </div>
          {importResult && (
            <div className="p-3 bg-calm-green/10 text-calm-green text-sm rounded">
              {importResult}
              <button className="ml-2 underline" onClick={() => setImportResult(null)}>dismiss</button>
            </div>
          )}
        </div>
      </Card>

      {/* Account */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Account</h3>
        <Button variant="ghost" onClick={logout}>Sign out</Button>
      </Card>
    </div>
  );
}
