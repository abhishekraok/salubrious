import { useApi } from '../hooks/useApi';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

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

const COLORS = [
  '#7C9A8E', // sage green
  '#B8926A', // warm tan
  '#8B7EA8', // muted purple
  '#C47D6A', // dusty coral
  '#6B8CAE', // steel blue
  '#A89B6B', // olive gold
];

/**
 * A single gauge ring.
 * - Gray background track (full circle)
 * - Colored arc for current %
 * - Tick mark + label for target %
 * - Center text: current value and delta
 */
function GaugeRing({
  label,
  current,
  target,
  max,
  color,
}: {
  label: string;
  current: number;
  target: number;
  max: number;
  color: string;
}) {
  const size = 120;
  const cx = size / 2, cy = size / 2;
  const radius = 44;
  const stroke = 10;
  const circumference = 2 * Math.PI * radius;

  // Current arc
  const currentFrac = max > 0 ? Math.min(current / max, 1) : 0;
  const dashLen = currentFrac * circumference;

  // Target tick position (angle from top, clockwise)
  const targetFrac = max > 0 ? Math.min(target / max, 1) : 0;
  const targetAngle = targetFrac * 360 - 90; // -90 to start from top
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
        {/* Background track */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none" stroke="#E8E6E1" strokeWidth={stroke}
        />
        {/* Current value arc */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dashLen} ${circumference}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        {/* Target tick mark */}
        <line
          x1={tx1} y1={ty1} x2={tx2} y2={ty2}
          stroke="#3D3D3D" strokeWidth={2.5} strokeLinecap="round"
        />
        {/* Center: current value */}
        <text x={cx} y={cy - 4} textAnchor="middle" className="text-sm font-semibold fill-calm-text">
          {current.toFixed(1)}%
        </text>
        {/* Center: delta */}
        <text x={cx} y={cy + 12} textAnchor="middle" className="text-[10px]" fill={deltaColor}>
          {deltaStr}pp
        </text>
      </svg>
      <span className="text-xs text-calm-text mt-1 font-medium">{label}</span>
      <span className="text-[10px] text-calm-muted">target {target.toFixed(1)}%</span>
    </div>
  );
}

function pick(entries: BreakdownEntry[], label: string) {
  return entries.find((e) => e.label === label) ?? null;
}

function driftStatus(current: number, target: number): 'ok' | 'watch' | 'action_needed' {
  const absDrift = Math.abs(current - target);
  if (absDrift < 2) return 'ok';
  if (absDrift < 5) return 'watch';
  return 'action_needed';
}

function SingleGauge({ title, entry, color }: { title: string; entry: BreakdownEntry; color: string }) {
  const status = driftStatus(entry.current_pct, entry.target_pct);
  return (
    <Card>
      <h3 className="text-sm font-medium text-calm-muted uppercase tracking-wide mb-4">{title}</h3>
      <div className="flex flex-col items-center">
        <GaugeRing
          label={entry.label}
          current={entry.current_pct}
          target={entry.target_pct}
          max={100}
          color={color}
        />
        <div className="mt-2">
          <Badge status={status}>
            {status === 'ok' ? 'OK' : status === 'watch' ? 'Watch' : 'Action'}
          </Badge>
        </div>
      </div>
    </Card>
  );
}

export function InsightsPage() {
  const { data } = useApi<BreakdownData>('/insights/breakdown');

  if (!data) {
    return <p className="text-calm-muted text-sm">Loading...</p>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">Portfolio Insights</h2>
      <p className="text-sm text-calm-muted">Region and factor breakdowns are computed on equities only.</p>

      <div className="grid grid-cols-2 gap-6">
        {pick(data.asset_type, 'Equities') && (
          <SingleGauge title="Equity %" entry={pick(data.asset_type, 'Equities')!} color={COLORS[0]} />
        )}
        {pick(data.region, 'International') && (
          <SingleGauge title="International %" entry={pick(data.region, 'International')!} color={COLORS[1]} />
        )}
        {pick(data.factor_value, 'Tilted') && (
          <SingleGauge title="Value-Tilted %" entry={pick(data.factor_value, 'Tilted')!} color={COLORS[2]} />
        )}
        {pick(data.factor_size, 'Small Cap') && (
          <SingleGauge title="Small Cap %" entry={pick(data.factor_size, 'Small Cap')!} color={COLORS[3]} />
        )}
      </div>
    </div>
  );
}
