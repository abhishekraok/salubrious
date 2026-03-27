import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useApi } from '../hooks/useApi';
import type { TodayRecommendation } from '../types';

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

const COLORS = ['#7C9A8E', '#B8926A', '#8B7EA8', '#C47D6A'];

function GaugeRing({ label, current, target, max, color }: {
  label: string; current: number; target: number; max: number; color: string;
}) {
  const size = 120;
  const cx = size / 2, cy = size / 2;
  const radius = 44;
  const stroke = 10;
  const circumference = 2 * Math.PI * radius;

  const currentFrac = max > 0 ? Math.min(current / max, 1) : 0;
  const dashLen = currentFrac * circumference;

  const targetFrac = max > 0 ? Math.min(target / max, 1) : 0;
  const targetAngle = targetFrac * 360 - 90;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const tickInner = radius - stroke / 2 - 3;
  const tickOuter = radius + stroke / 2 + 3;
  const tx1 = cx + tickInner * Math.cos(toRad(targetAngle));
  const ty1 = cy + tickInner * Math.sin(toRad(targetAngle));
  const tx2 = cx + tickOuter * Math.cos(toRad(targetAngle));
  const ty2 = cy + tickOuter * Math.sin(toRad(targetAngle));

  const delta = current - target;
  const deltaStr = delta >= 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1);
  const deltaColor = Math.abs(delta) < 1 ? '#7C9A8E' : Math.abs(delta) < 3 ? '#C4A24D' : '#C47D6A';

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#E8E6E1" strokeWidth={stroke} />
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dashLen} ${circumference}`} strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`} />
        <line x1={tx1} y1={ty1} x2={tx2} y2={ty2} stroke="#3D3D3D" strokeWidth={2.5} strokeLinecap="round" />
        <text x={cx} y={cy - 4} textAnchor="middle" className="text-sm font-semibold fill-calm-text">
          {current.toFixed(1)}%
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="text-[10px]" fill={deltaColor}>
          {deltaStr}pp
        </text>
      </svg>
      <span className="text-xs text-calm-text mt-1 font-medium">{label}</span>
      <span className="text-[10px] text-calm-muted">target {target.toFixed(1)}%</span>
    </div>
  );
}

function driftStatus(current: number, target: number): 'ok' | 'watch' | 'action_needed' {
  const absDrift = Math.abs(current - target);
  if (absDrift < 2) return 'ok';
  if (absDrift < 5) return 'watch';
  return 'action_needed';
}

function pick(entries: BreakdownEntry[], label: string) {
  return entries.find((e) => e.label === label) ?? null;
}

function InsightGauge({ title, entry, color, basis }: { title: string; entry: BreakdownEntry; color: string; basis: string }) {
  const status = driftStatus(entry.current_pct, entry.target_pct);
  return (
    <div className="flex flex-col items-center">
      <GaugeRing label={entry.label} current={entry.current_pct} target={entry.target_pct} max={100} color={color} />
      <span className="text-[10px] text-calm-muted">{basis}</span>
      <div className="mt-1">
        <Badge status={status}>{status === 'ok' ? 'OK' : status === 'watch' ? 'Watch' : 'Action'}</Badge>
      </div>
    </div>
  );
}

export function TodayPage() {
  const { data, loading } = useApi<TodayRecommendation>('/recommendation/today');
  const { data: breakdown } = useApi<BreakdownData>('/insights/breakdown');

  if (loading || !data) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  const borderColor = {
    calm: 'border-l-calm-green',
    watch: 'border-l-calm-amber',
    action: 'border-l-calm-red',
  }[data.status];

  const headlineColor = {
    calm: 'text-calm-green',
    watch: 'text-calm-amber',
    action: 'text-calm-red',
  }[data.status];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Today</h2>

      {/* Primary recommendation card */}
      <Card className={`border-l-4 ${borderColor}`}>
        <div className="space-y-2">
          <p className={`text-lg font-medium ${headlineColor}`}>{data.headline}</p>
          <p className="text-sm text-calm-muted">{data.explanation}</p>
        </div>
      </Card>

      {/* Portfolio Insights */}
      {breakdown && (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-4">Portfolio Insights</h3>
          <div className="grid grid-cols-4 gap-4">
            {pick(breakdown.asset_type, 'Equities') && (
              <InsightGauge title="Equity %" entry={pick(breakdown.asset_type, 'Equities')!} color={COLORS[0]} basis="of portfolio" />
            )}
            {pick(breakdown.region, 'International') && (
              <InsightGauge title="International %" entry={pick(breakdown.region, 'International')!} color={COLORS[1]} basis="of equities" />
            )}
            {pick(breakdown.factor_value, 'Tilted') && (
              <InsightGauge title="Value-Tilted %" entry={pick(breakdown.factor_value, 'Tilted')!} color={COLORS[2]} basis="of equities" />
            )}
            {pick(breakdown.factor_size, 'Small Cap') && (
              <InsightGauge title="Small Cap %" entry={pick(breakdown.factor_size, 'Small Cap')!} color={COLORS[3]} basis="of value-tilted" />
            )}
          </div>
        </Card>
      )}

      {/* Active issues */}
      {data.active_issues.length > 0 ? (
        <Card>
          <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Active Issues</h3>
          <ul className="space-y-2">
            {data.active_issues.map((issue, i) => (
              <li key={i} className="text-sm text-calm-text flex items-start gap-2">
                <span className="text-calm-amber mt-0.5">&#x2022;</span>
                {issue}
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <Card className="border-l-4 border-l-calm-green/30">
          <p className="text-sm text-calm-muted">
            Everything is within policy. You do not need to act.
          </p>
        </Card>
      )}

      {/* Status summary — single row */}
      <Card>
        <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-3">Status</h3>
        <div className="grid grid-cols-4 gap-4">
          {data.summary_cards.map((card) => (
            <div key={card.label}>
              <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">{card.label}</p>
              <p className="text-lg font-medium">{card.value}</p>
              <Badge status={card.status as 'calm' | 'watch' | 'action'}>{card.status}</Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
