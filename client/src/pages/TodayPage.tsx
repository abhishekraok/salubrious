import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useApi } from '../hooks/useApi';
import type { TodayRecommendation } from '../types';

export function TodayPage() {
  const { data, loading } = useApi<TodayRecommendation>('/recommendation/today');

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

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4">
        {data.summary_cards.map((card) => (
          <Card key={card.label}>
            <p className="text-xs text-calm-muted uppercase tracking-wide mb-1">{card.label}</p>
            <p className="text-lg font-medium">{card.value}</p>
            <Badge status={card.status as 'calm' | 'watch' | 'action'}>{card.status}</Badge>
          </Card>
        ))}
      </div>

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
    </div>
  );
}
