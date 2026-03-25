import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { post, put } from '../api/client';
import type { SpendingRunway, SpendingGuidance, InvestmentPolicy } from '../types';

function formatDollars(n: number) {
  return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

interface ScenarioResult {
  description: string;
  adjusted_runway_years: number;
  adjusted_funded_status: string;
  impact_summary: string;
}

/* SVG Gauge for spending guidance */
function SpendingGauge({ current, recommended, status }: {
  current: number;
  recommended: number;
  status: 'low' | 'appropriate' | 'high';
}) {
  const size = 160;
  const stroke = 14;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;

  // Map spending ratio to arc: 0% = empty, 200% of recommended = full
  const ratio = recommended > 0 ? current / recommended : 0;
  const clampedRatio = Math.min(ratio, 2);
  const arcFraction = clampedRatio / 2; // full circle = 200% of recommended
  const arcLength = circumference * arcFraction;

  // Target tick at 50% of arc (= 100% of recommended)
  const targetAngle = -90 + (0.5 * 360); // 50% around = 90 degrees
  const targetRad = (targetAngle * Math.PI) / 180;
  const tickInner = r - stroke / 2 - 2;
  const tickOuter = r + stroke / 2 + 2;

  const colors = {
    low: '#6b8e7b',      // sage green (muted)
    appropriate: '#6b8e7b',
    high: '#c4785b',     // warm amber-red
  };
  const arcColor = colors[status];

  const pctOfRecommended = recommended > 0 ? Math.round((current / recommended) * 100) : 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Background track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e5e0" strokeWidth={stroke} />
      {/* Current spending arc */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={arcColor}
        strokeWidth={stroke}
        strokeDasharray={`${arcLength} ${circumference - arcLength}`}
        strokeDashoffset={circumference * 0.25}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
      />
      {/* Target tick mark */}
      <line
        x1={cx + tickInner * Math.cos(targetRad)}
        y1={cy + tickInner * Math.sin(targetRad)}
        x2={cx + tickOuter * Math.cos(targetRad)}
        y2={cy + tickOuter * Math.sin(targetRad)}
        stroke="#555"
        strokeWidth={2.5}
        strokeLinecap="round"
      />
      {/* Center text */}
      <text x={cx} y={cy - 8} textAnchor="middle" className="text-lg font-semibold fill-calm-text">
        {pctOfRecommended}%
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" className="text-[10px] fill-calm-muted">
        of recommended
      </text>
    </svg>
  );
}

export function SpendingPage() {
  const { data: runway } = useApi<SpendingRunway>('/spending/runway');
  const { data: guidance, refetch: refetchGuidance } = useApi<SpendingGuidance>('/spending/guidance');
  const { data: policy, refetch: refetchPolicy } = useApi<InvestmentPolicy>('/policy');
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [scenarioInputs, setScenarioInputs] = useState({
    spending_delta: 0,
    portfolio_shock_percent: 0,
  });
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    expected_years_remaining: '',
    expected_years_earning: '',
    expected_after_tax_salary: '',
    withdrawal_rate_pct: '',
    baseline_annual_spending: '',
    comfortable_annual_spending: '',
    emergency_annual_spending: '',
  });

  if (!runway || !policy || !guidance) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const startEditing = () => {
    setForm({
      expected_years_remaining: policy.expected_years_remaining?.toString() || '',
      expected_years_earning: policy.expected_years_earning?.toString() || '',
      expected_after_tax_salary: policy.expected_after_tax_salary?.toString() || '',
      withdrawal_rate_pct: policy.withdrawal_rate_pct?.toString() || '3.5',
      baseline_annual_spending: policy.baseline_annual_spending?.toString() || '',
      comfortable_annual_spending: policy.comfortable_annual_spending?.toString() || '',
      emergency_annual_spending: policy.emergency_annual_spending?.toString() || '',
    });
    setEditing(true);
  };

  const saveForm = async () => {
    await put('/policy', {
      expected_years_remaining: form.expected_years_remaining ? Number(form.expected_years_remaining) : null,
      expected_years_earning: form.expected_years_earning ? Number(form.expected_years_earning) : null,
      expected_after_tax_salary: form.expected_after_tax_salary ? Number(form.expected_after_tax_salary) : null,
      withdrawal_rate_pct: Number(form.withdrawal_rate_pct) || 3.5,
      baseline_annual_spending: Number(form.baseline_annual_spending) || 0,
      comfortable_annual_spending: Number(form.comfortable_annual_spending) || 0,
      emergency_annual_spending: Number(form.emergency_annual_spending) || 0,
    });
    setEditing(false);
    refetchPolicy();
    refetchGuidance();
  };

  const fundedBadge = {
    secure: 'calm' as const,
    watch: 'watch' as const,
    constrained: 'action' as const,
  }[runway.funded_status] || 'calm' as const;

  const guidanceBadge = {
    low: 'calm' as const,
    appropriate: 'calm' as const,
    high: 'action' as const,
  }[guidance.spending_status] || 'calm' as const;

  const guidanceLabel = {
    low: 'Below recommended — you could spend more',
    appropriate: 'Spending is in a healthy range',
    high: 'Above recommended — consider reducing',
  }[guidance.spending_status];

  const runScenario = async () => {
    const result = await post<ScenarioResult>('/spending/scenario', scenarioInputs);
    setScenario(result);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Spending</h2>
        <Button variant="secondary" onClick={editing ? saveForm : startEditing}>
          {editing ? 'Save' : 'Edit Parameters'}
        </Button>
      </div>

      {/* Spending Guidance */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-4">Spending Guidance</h3>
        <div className="flex items-start gap-8">
          <SpendingGauge
            current={guidance.current_baseline_spending}
            recommended={guidance.recommended_annual_spending}
            status={guidance.spending_status}
          />
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs text-calm-muted">Recommended Annual Spending</p>
              <p className="text-2xl font-semibold">{formatDollars(guidance.recommended_annual_spending)}</p>
              <p className="text-xs text-calm-muted mt-0.5">
                {guidance.withdrawal_rate_pct}% of {formatDollars(guidance.total_portfolio_value)} portfolio
              </p>
            </div>
            <div>
              <p className="text-xs text-calm-muted">Current Baseline Spending</p>
              <p className="text-lg font-medium">{formatDollars(guidance.current_baseline_spending)}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge status={guidanceBadge}>
                {guidance.spending_status === 'low' ? 'Low' : guidance.spending_status === 'high' ? 'High' : 'OK'}
              </Badge>
              <span className="text-sm text-calm-muted">{guidanceLabel}</span>
            </div>
          </div>
        </div>
        {guidance.future_earnings_present_value > 0 && (
          <div className="mt-4 pt-3 border-t border-calm-border text-sm text-calm-muted">
            <p>
              Future earnings (PV): {formatDollars(guidance.future_earnings_present_value)} &middot;
              Effective wealth: {formatDollars(guidance.effective_wealth)}
            </p>
          </div>
        )}
      </Card>

      {/* Editable parameters */}
      {editing && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Parameters</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label className="text-xs text-calm-muted block mb-1">Expected years remaining</label>
              <input
                type="number"
                value={form.expected_years_remaining}
                onChange={(e) => setForm({ ...form, expected_years_remaining: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">Years still earning</label>
              <input
                type="number"
                value={form.expected_years_earning}
                onChange={(e) => setForm({ ...form, expected_years_earning: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">After-tax salary ($/yr)</label>
              <input
                type="number"
                value={form.expected_after_tax_salary}
                onChange={(e) => setForm({ ...form, expected_after_tax_salary: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">Withdrawal rate (%)</label>
              <input
                type="number"
                step="0.1"
                value={form.withdrawal_rate_pct}
                onChange={(e) => setForm({ ...form, withdrawal_rate_pct: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">Baseline spending ($/yr)</label>
              <input
                type="number"
                value={form.baseline_annual_spending}
                onChange={(e) => setForm({ ...form, baseline_annual_spending: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">Comfortable spending ($/yr)</label>
              <input
                type="number"
                value={form.comfortable_annual_spending}
                onChange={(e) => setForm({ ...form, comfortable_annual_spending: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
            <div>
              <label className="text-xs text-calm-muted block mb-1">Emergency spending ($/yr)</label>
              <input
                type="number"
                value={form.emergency_annual_spending}
                onChange={(e) => setForm({ ...form, emergency_annual_spending: e.target.value })}
                className="w-full px-3 py-1.5 border border-calm-border rounded bg-calm-surface"
              />
            </div>
          </div>
        </Card>
      )}

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

      {/* Summary */}
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
