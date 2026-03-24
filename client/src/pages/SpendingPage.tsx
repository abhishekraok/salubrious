import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { post } from '../api/client';
import type { SpendingRunway, InvestmentPolicy } from '../types';

function formatDollars(n: number) {
  return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

interface ScenarioResult {
  description: string;
  adjusted_runway_years: number;
  adjusted_funded_status: string;
  impact_summary: string;
}

export function SpendingPage() {
  const { data: runway } = useApi<SpendingRunway>('/spending/runway');
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [scenarioInputs, setScenarioInputs] = useState({
    spending_delta: 0,
    portfolio_shock_percent: 0,
  });

  if (!runway || !policy) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const fundedBadge = {
    secure: 'calm' as const,
    watch: 'watch' as const,
    constrained: 'action' as const,
  }[runway.funded_status] || 'calm' as const;

  const runScenario = async () => {
    const result = await post<ScenarioResult>('/spending/scenario', scenarioInputs);
    setScenario(result);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Spending</h2>

      {/* Core metrics */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Safe Assets</p>
          <p className="text-lg font-medium">{formatDollars(runway.safe_asset_total)}</p>
        </Card>
        <Card>
          <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Cash-like</p>
          <p className="text-lg font-medium">{formatDollars(runway.cash_like_total)}</p>
        </Card>
        <Card>
          <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Funded Status</p>
          <p className="text-lg font-medium capitalize">{runway.funded_status}</p>
          <Badge status={fundedBadge}>{runway.funded_status}</Badge>
        </Card>
      </div>

      {/* Runway */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Spending Runway</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span>Baseline spending ({formatDollars(policy.baseline_annual_spending)}/yr)</span>
            <span className="font-medium">{runway.baseline_runway_years} years</span>
          </div>
          <div className="flex justify-between">
            <span>Comfortable spending ({formatDollars(policy.comfortable_annual_spending)}/yr)</span>
            <span className="font-medium">{runway.comfortable_runway_years} years</span>
          </div>
          <div className="flex justify-between">
            <span>Emergency spending ({formatDollars(policy.emergency_annual_spending)}/yr)</span>
            <span className="font-medium">{runway.emergency_runway_years} years</span>
          </div>
          <div className="flex justify-between border-t border-calm-border pt-3">
            <span>Cash runway</span>
            <span className="font-medium">{runway.cash_runway_years} years</span>
          </div>
        </div>
      </Card>

      {/* Derived messages */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Summary</h3>
        <ul className="space-y-2 text-sm">
          <li>Safe assets cover {runway.baseline_runway_years} years of baseline spending.</li>
          <li>
            You are {runway.above_minimum_reserve_by >= 0 ? 'above' : 'below'} your minimum reserve target by{' '}
            {formatDollars(Math.abs(runway.above_minimum_reserve_by))}.
          </li>
          <li>Target runway: {policy.safe_asset_runway_years_target} years.</li>
        </ul>
      </Card>

      {/* Scenario */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">What-If Scenario</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-calm-muted block mb-1">Spending change ($/yr)</label>
            <input
              type="number"
              value={scenarioInputs.spending_delta || ''}
              onChange={(e) => setScenarioInputs({ ...scenarioInputs, spending_delta: Number(e.target.value) })}
              placeholder="e.g. 10000"
              className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface"
            />
          </div>
          <div>
            <label className="text-xs text-calm-muted block mb-1">Portfolio shock (%)</label>
            <input
              type="number"
              value={scenarioInputs.portfolio_shock_percent || ''}
              onChange={(e) => setScenarioInputs({ ...scenarioInputs, portfolio_shock_percent: Number(e.target.value) })}
              placeholder="e.g. -20"
              className="w-full px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface"
            />
          </div>
        </div>
        <Button variant="secondary" onClick={runScenario}>Run Scenario</Button>

        {scenario && (
          <div className="mt-4 p-3 bg-calm-bg rounded text-sm">
            <p className="font-medium">{scenario.description}</p>
            <p className="mt-1">{scenario.impact_summary}</p>
            <p className="mt-1">
              Status: <span className="capitalize font-medium">{scenario.adjusted_funded_status}</span>
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
