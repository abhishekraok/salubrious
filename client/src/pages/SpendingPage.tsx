import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { post, put } from '../api/client';
import type { SpendingRunway, SpendingGuidance, InvestmentPolicy, SimulationResult } from '../types';

function formatDollars(n: number) {
  return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function formatCompact(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

interface ScenarioResult {
  description: string;
  adjusted_runway_years: number;
  adjusted_funded_status: string;
  impact_summary: string;
}

/* Stacked bar showing two segments with labels */
function StackedBar({ segments, total }: {
  segments: { label: string; value: number; color: string }[];
  total: number;
}) {
  return (
    <div>
      <div className="flex h-7 rounded-md overflow-hidden bg-calm-border/30">
        {segments.map((seg, i) => {
          const pct = total > 0 ? (seg.value / total) * 100 : 0;
          if (pct <= 0) return null;
          return (
            <div
              key={i}
              className="flex items-center justify-center text-[10px] font-medium text-white transition-all"
              style={{ width: `${pct}%`, backgroundColor: seg.color }}
              title={`${seg.label}: ${formatDollars(seg.value)}`}
            >
              {pct > 12 ? formatDollars(seg.value) : ''}
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 mt-1.5">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs text-calm-muted">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: seg.color }} />
            {seg.label}
          </div>
        ))}
      </div>
    </div>
  );
}

/* SVG fan chart for wealth trajectory */
function WealthTrajectoryChart({ sim }: { sim: SimulationResult }) {
  const W = 600;
  const H = 280;
  const pad = { top: 20, right: 20, bottom: 40, left: 65 };
  const chartW = W - pad.left - pad.right;
  const chartH = H - pad.top - pad.bottom;

  const n = sim.years.length;
  const maxVal = Math.max(...sim.p95);

  // Log scale: floor at median/100 to keep bands visible, max from p95
  const medianMax = Math.max(...sim.p50.filter(v => v > 0));
  const logFloor = Math.max(medianMax / 100, 1);
  const logMax = Math.log10(Math.max(maxVal, 10));
  const logMin = Math.log10(logFloor);
  const logRange = logMax - logMin;

  const x = (i: number) => pad.left + (i / (n - 1)) * chartW;
  const y = (v: number) => {
    const logV = Math.log10(Math.max(v, logFloor));
    return pad.top + chartH - ((logV - logMin) / logRange) * chartH;
  };

  // Build area paths for percentile bands
  const bandPath = (upper: number[], lower: number[]) => {
    const forward = upper.map((_, i) => `${x(i)},${y(upper[i])}`).join(' L');
    const backward = [...lower].reverse().map((_, i) => `${x(n - 1 - i)},${y(lower[n - 1 - i])}`).join(' L');
    return `M${forward} L${backward} Z`;
  };

  // Y-axis ticks: powers of 10 that fit in range
  const yTicks: number[] = [];
  for (let exp = Math.floor(logMin); exp <= Math.ceil(logMax); exp++) {
    const val = Math.pow(10, exp);
    if (val >= logFloor && val <= Math.pow(10, logMax)) {
      yTicks.push(val);
    }
  }

  // X-axis ticks (every 10 years)
  const xTicks = sim.years.filter(yr => yr % 10 === 0 || yr === sim.years[sim.years.length - 1]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: '320px' }}>
      {/* Grid lines */}
      {yTicks.map((v, i) => (
        <line key={i} x1={pad.left} x2={W - pad.right} y1={y(v)} y2={y(v)}
          stroke="#e5e5e0" strokeWidth={0.5} />
      ))}

      {/* 5th-95th band */}
      <path d={bandPath(sim.p95, sim.p5)} fill="#6b8e7b" opacity={0.12} />
      {/* 25th-75th band */}
      <path d={bandPath(sim.p75, sim.p25)} fill="#6b8e7b" opacity={0.2} />

      {/* Median line */}
      <polyline
        points={sim.p50.map((v, i) => `${x(i)},${y(v)}`).join(' ')}
        fill="none" stroke="#6b8e7b" strokeWidth={2}
      />

      {/* Zero line */}
      <line x1={pad.left} x2={W - pad.right} y1={y(0)} y2={y(0)}
        stroke="#c4785b" strokeWidth={1} strokeDasharray="4,3" opacity={0.6} />

      {/* Y-axis labels */}
      {yTicks.map((v, i) => (
        <text key={i} x={pad.left - 8} y={y(v) + 4} textAnchor="end"
          className="text-[10px] fill-calm-muted">{formatCompact(v)}</text>
      ))}

      {/* X-axis labels */}
      {xTicks.map((yr) => (
        <text key={yr} x={x(yr)} y={H - pad.bottom + 18} textAnchor="middle"
          className="text-[10px] fill-calm-muted">Yr {yr}</text>
      ))}

      {/* Axis lines */}
      <line x1={pad.left} x2={pad.left} y1={pad.top} y2={H - pad.bottom}
        stroke="#ccc" strokeWidth={1} />
      <line x1={pad.left} x2={W - pad.right} y1={H - pad.bottom} y2={H - pad.bottom}
        stroke="#ccc" strokeWidth={1} />
    </svg>
  );
}

export function SpendingPage() {
  const { data: runway } = useApi<SpendingRunway>('/spending/runway');
  const { data: guidance, refetch: refetchGuidance } = useApi<SpendingGuidance>('/spending/guidance');
  const { data: policy, refetch: refetchPolicy } = useApi<InvestmentPolicy>('/policy');
  const { data: simulation } = useApi<SimulationResult>('/spending/simulation');
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

  const ruinColor = simulation
    ? simulation.ruin_probability <= 0.05 ? '#6b8e7b'
    : simulation.ruin_probability <= 0.15 ? '#c9a227'
    : '#c4785b'
    : '#6b8e7b';

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

        <div className="space-y-5">
          {/* Spending bar */}
          <div>
            <div className="flex items-baseline justify-between mb-2">
              <p className="text-sm font-medium">Annual Spending</p>
              <div className="flex items-center gap-2">
                <Badge status={guidanceBadge}>
                  {guidance.spending_status === 'low' ? 'Low' : guidance.spending_status === 'high' ? 'High' : 'OK'}
                </Badge>
                <span className="text-xs text-calm-muted">{guidanceLabel}</span>
              </div>
            </div>
            <StackedBar
              segments={[
                { label: `Current: ${formatDollars(guidance.current_baseline_spending)}`, value: guidance.current_baseline_spending, color: guidance.spending_status === 'high' ? '#c4785b' : '#6b8e7b' },
                { label: `Recommended: ${formatDollars(guidance.recommended_annual_spending)}`, value: guidance.recommended_annual_spending - guidance.current_baseline_spending, color: '#d4d4c8' },
              ].filter(s => s.value > 0)}
              total={Math.max(guidance.recommended_annual_spending, guidance.current_baseline_spending)}
            />
            <p className="text-xs text-calm-muted mt-1.5">
              {guidance.withdrawal_rate_pct}% of{' '}
              {guidance.future_earnings_present_value > 0
                ? `${formatDollars(guidance.effective_wealth)} effective wealth`
                : `${formatDollars(guidance.total_portfolio_value)} portfolio`}
            </p>
          </div>

          {/* Wealth bar */}
          <div>
            <p className="text-sm font-medium mb-2">Wealth</p>
            <StackedBar
              segments={[
                { label: `Portfolio: ${formatDollars(guidance.total_portfolio_value)}`, value: guidance.total_portfolio_value, color: '#6b8e7b' },
                ...(guidance.future_earnings_present_value > 0
                  ? [{ label: `Future earnings (PV): ${formatDollars(guidance.future_earnings_present_value)}`, value: guidance.future_earnings_present_value, color: '#a3b8a0' }]
                  : []),
              ]}
              total={guidance.effective_wealth || guidance.total_portfolio_value}
            />
            {guidance.future_earnings_present_value > 0 && (
              <p className="text-xs text-calm-muted mt-1.5">
                Effective wealth: {formatDollars(guidance.effective_wealth)}
                {guidance.years_earning && ` (${guidance.years_earning} earning years remaining)`}
              </p>
            )}
          </div>
        </div>
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

      {/* Monte Carlo Simulation */}
      {simulation && (
        <Card>
          <div className="flex items-baseline justify-between mb-4">
            <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide">Wealth Trajectory</h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-calm-muted">
                Ruin probability:
              </span>
              <span className="text-lg font-semibold" style={{ color: ruinColor }}>
                {(simulation.ruin_probability * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          <WealthTrajectoryChart sim={simulation} />

          <div className="flex items-center gap-6 mt-3 text-xs text-calm-muted">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-3 rounded-sm" style={{ backgroundColor: '#6b8e7b', opacity: 0.12 }} />
              5th–95th percentile
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-3 rounded-sm" style={{ backgroundColor: '#6b8e7b', opacity: 0.3 }} />
              25th–75th percentile
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-1 rounded-sm" style={{ backgroundColor: '#6b8e7b' }} />
              Median
            </div>
          </div>

          <p className="text-xs text-calm-muted mt-3">
            2,000 simulations using historical return distributions.
            Spending: {formatDollars(policy.baseline_annual_spending)}/yr.
            {policy.expected_years_earning && policy.expected_years_earning > 0 &&
              ` Salary of ${formatDollars(policy.expected_after_tax_salary || 0)}/yr for ${policy.expected_years_earning} years.`}
          </p>
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
