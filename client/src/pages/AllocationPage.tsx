import { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import type { AllocationResult, InvestmentPolicy, RebalanceSuggestion } from '../types';

interface BreakdownEntry {
  label: string;
  current_pct: number;
  target_pct: number;
}

interface BreakdownData {
  asset_type: BreakdownEntry[];
  region: BreakdownEntry[];
  factor_value: BreakdownEntry[];
  factor_size: BreakdownEntry[];
}

function formatDollars(n: number) {
  return '$' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function CategoryDriftTable({ breakdown }: { breakdown: BreakdownData }) {
  const sections: { title: string; entries: BreakdownEntry[] }[] = [
    { title: 'Equity vs Safe Assets', entries: breakdown.asset_type },
    { title: 'US vs International', entries: breakdown.region },
    { title: 'Value Exposure', entries: breakdown.factor_value },
    { title: 'Small Cap Exposure', entries: breakdown.factor_size },
  ];

  return (
    <Card>
      <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Category Allocation</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
            <th className="pb-2 pr-4">Category</th>
            <th className="pb-2 pr-4 text-right">Current %</th>
            <th className="pb-2 pr-4 text-right">Target %</th>
            <th className="pb-2 pr-4 text-right">Drift (pp)</th>
            <th className="pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {sections.map((section) => (
            <>
              <tr key={section.title}>
                <td colSpan={5} className="pt-3 pb-1 text-xs font-medium text-calm-muted uppercase tracking-wide">
                  {section.title}
                </td>
              </tr>
              {section.entries.map((e) => {
                const drift = e.current_pct - e.target_pct;
                const absDrift = Math.abs(drift);
                const status = absDrift < 2 ? 'ok' : absDrift < 5 ? 'watch' : 'action_needed';
                const rowBg = status === 'action_needed' ? 'bg-calm-red/5' : status === 'watch' ? 'bg-calm-amber/5' : '';
                return (
                  <tr key={`${section.title}-${e.label}`} className={`border-b border-calm-border/50 ${rowBg}`}>
                    <td className="py-2 pr-4 font-medium">{e.label}</td>
                    <td className="py-2 pr-4 text-right">{e.current_pct.toFixed(1)}%</td>
                    <td className="py-2 pr-4 text-right">{e.target_pct.toFixed(1)}%</td>
                    <td className="py-2 pr-4 text-right">
                      <span className={status === 'action_needed' ? 'text-calm-red' : status === 'watch' ? 'text-calm-amber' : ''}>
                        {drift > 0 ? '+' : ''}{drift.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2">
                      <Badge status={status}>
                        {status === 'ok' ? 'OK' : status === 'watch' ? 'Watch' : 'Action'}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export function AllocationPage() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  const { data: allocation, loading } = useApi<AllocationResult>('/allocation/current');
  const { data: suggestion } = useApi<RebalanceSuggestion>('/allocation/suggested-actions');
  const { data: breakdown } = useApi<BreakdownData>('/insights/breakdown');
  const [pendingCash, setPendingCash] = useState('');
  const { data: cashSuggestion, refetch: refetchCash } = useApi<RebalanceSuggestion>(
    `/allocation/suggested-actions?pending_cash=${pendingCash || '0'}`
  );

  if (loading || !allocation || !policy) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const isCategory = policy.targeting_mode === 'category';
  const activeSuggestion = pendingCash ? cashSuggestion : suggestion;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Allocation</h2>

      {/* Summary */}
      <div className={`grid ${isCategory ? 'grid-cols-2' : 'grid-cols-4'} gap-4`}>
        <Card>
          <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Total Value</p>
          <p className="text-lg font-medium">{formatDollars(allocation.total_value)}</p>
        </Card>
        <Card>
          <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Sleeves</p>
          <p className="text-lg font-medium">{allocation.sleeves.length}</p>
        </Card>
        {!isCategory && (
          <>
            <Card>
              <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Outside Soft Band</p>
              <p className="text-lg font-medium">{allocation.sleeves_outside_soft}</p>
            </Card>
            <Card>
              <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">Outside Hard Band</p>
              <p className="text-lg font-medium">{allocation.sleeves_outside_hard}</p>
            </Card>
          </>
        )}
      </div>

      {/* Category mode: category drift table */}
      {isCategory && breakdown && <CategoryDriftTable breakdown={breakdown} />}

      {/* Fund mode: per-fund allocation table */}
      {!isCategory && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                  <th className="pb-2 pr-4">Asset</th>
                  <th className="pb-2 pr-4 text-right">Value</th>
                  <th className="pb-2 pr-4 text-right">Current %</th>
                  <th className="pb-2 pr-4 text-right">Target %</th>
                  <th className="pb-2 pr-4 text-right">Drift (pp)</th>
                  <th className="pb-2 pr-4 text-right">Band</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {allocation.sleeves.map((s) => {
                  const rowBg = s.status === 'action_needed'
                    ? 'bg-calm-red/5'
                    : s.status === 'watch'
                    ? 'bg-calm-amber/5'
                    : '';
                  return (
                    <tr key={s.ticker} className={`border-b border-calm-border/50 ${rowBg}`}>
                      <td className="py-2.5 pr-4">
                        <span className="font-medium">{s.ticker}</span>
                        <span className="text-calm-muted ml-2">{s.label}</span>
                      </td>
                      <td className="py-2.5 pr-4 text-right">{formatDollars(s.current_value)}</td>
                      <td className="py-2.5 pr-4 text-right">{s.current_percent.toFixed(1)}%</td>
                      <td className="py-2.5 pr-4 text-right">{s.target_percent.toFixed(1)}%</td>
                      <td className="py-2.5 pr-4 text-right">
                        <span className={
                          s.status === 'action_needed' ? 'text-calm-red' :
                          s.status === 'watch' ? 'text-calm-amber' : ''
                        }>
                          {s.drift_pp > 0 ? '+' : ''}{s.drift_pp.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-right text-calm-muted">
                        {s.soft_band.toFixed(1)} / {s.hard_band.toFixed(1)}
                      </td>
                      <td className="py-2.5">
                        <Badge status={s.status}>
                          {s.status === 'ok' ? 'OK' : s.status === 'watch' ? 'Watch' : 'Action'}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Holdings list in category mode */}
      {isCategory && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Current Holdings</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-calm-border text-left text-xs text-calm-muted uppercase tracking-wide">
                <th className="pb-2 pr-4">Asset</th>
                <th className="pb-2 pr-4 text-right">Value</th>
                <th className="pb-2 text-right">Weight</th>
              </tr>
            </thead>
            <tbody>
              {allocation.sleeves.map((s) => (
                <tr key={s.ticker} className="border-b border-calm-border/50">
                  <td className="py-2 pr-4">
                    <span className="font-medium">{s.ticker}</span>
                    <span className="text-calm-muted ml-2">{s.label}</span>
                  </td>
                  <td className="py-2 pr-4 text-right">{formatDollars(s.current_value)}</td>
                  <td className="py-2 text-right">{s.current_percent.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Suggested action */}
      {activeSuggestion && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Suggested Action</h3>
          <p className="text-base font-medium mb-2">{activeSuggestion.headline}</p>
          <p className="text-sm text-calm-muted mb-4">{activeSuggestion.rationale}</p>

          {activeSuggestion.action_items.length > 0 && (
            <ul className="space-y-2 mb-4">
              {activeSuggestion.action_items.map((item, i) => (
                <li key={i} className="text-sm bg-calm-bg p-3 rounded">
                  <span className="font-medium capitalize">{item.action}</span>{' '}
                  {formatDollars(item.amount)} of <span className="font-medium">{item.ticker}</span>
                  {item.source_ticker && (
                    <> from <span className="font-medium">{item.source_ticker}</span></>
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* Pending cash input */}
          <div className="flex items-center gap-3 pt-3 border-t border-calm-border">
            <label className="text-sm text-calm-muted">Pending contribution:</label>
            <input
              type="number"
              value={pendingCash}
              onChange={(e) => setPendingCash(e.target.value)}
              onBlur={() => refetchCash()}
              placeholder="$0"
              className="w-32 px-3 py-1.5 text-sm border border-calm-border rounded bg-calm-surface"
            />
            <Button variant="secondary" onClick={() => refetchCash()}>
              Recalculate
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
