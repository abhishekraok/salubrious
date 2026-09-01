import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import type {
  DecisionMaturity,
  DecisionOutcome,
  DecisionQualityAction,
  DecisionQualityBenchmark,
  DecisionQualityCoverage,
  DecisionQualityPrimarySummary,
  DecisionQualityReconciliation,
  DecisionQualityResponse,
  DecisionQualitySummary,
  DecisionQualityYearBucket,
} from '../types';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});

const currencyFormatter = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const outcomeStyles: Record<DecisionOutcome, { bar: string; text: string; dot: string }> = {
  ahead: {
    bar: 'bg-calm-green',
    text: 'text-calm-green',
    dot: 'bg-calm-green',
  },
  similar: {
    bar: 'bg-calm-blue',
    text: 'text-calm-blue',
    dot: 'bg-calm-blue',
  },
  behind: {
    bar: 'bg-calm-red',
    text: 'text-calm-red',
    dot: 'bg-calm-red',
  },
};

type ScoredDecisionAction = DecisionQualityAction & {
  maturity: DecisionMaturity;
  outcome: DecisionOutcome;
  observed_days: number;
  chosen_return_pct: number;
  benchmark_return_pct: number;
  advantage_pct_points: number;
};

interface MatureYear {
  year: number;
  actions: ScoredDecisionAction[];
  ahead: number;
  similar: number;
  behind: number;
  weightedAdvantage: number | null;
}

function isScoredAction(action: DecisionQualityAction): action is ScoredDecisionAction {
  return action.score_status === 'scored'
    && (action.maturity === 'mature' || action.maturity === 'developing')
    && (action.outcome === 'ahead' || action.outcome === 'similar' || action.outcome === 'behind')
    && typeof action.observed_days === 'number'
    && typeof action.chosen_return_pct === 'number'
    && typeof action.benchmark_return_pct === 'number'
    && typeof action.advantage_pct_points === 'number';
}

function formatDate(value: string | null | undefined) {
  if (!value) return 'Not reported';
  const parsed = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return 'Not reported';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed);
}

function formatPp(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  const normalized = Math.abs(value) < 0.0005 ? 0 : value;
  const decimals = Math.abs(normalized) < 1 ? 2 : 1;
  const sign = normalized > 0 ? '+' : '';
  return `${sign}${normalized.toFixed(decimals)} pp`;
}

function formatReturn(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  const normalized = Math.abs(value) < 0.0005 ? 0 : value;
  const sign = normalized > 0 ? '+' : '';
  return `${sign}${normalized.toFixed(1)}%`;
}

function formatAccount(accountKey: string | undefined) {
  if (!accountKey) return 'Not reported';
  return accountKey
    .split(/[-_]/)
    .map((part) => {
      const upper = part.toUpperCase();
      if (upper === 'IRA' || upper === '401K') return upper;
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(' ');
}

function outcomeLabel(outcome: DecisionOutcome | null | undefined) {
  if (!outcome) return 'Not scored';
  return outcome.charAt(0).toUpperCase() + outcome.slice(1);
}

function weightedAdvantage(actions: ScoredDecisionAction[]) {
  const weighted = actions.filter((action) => action.notional > 0);
  const notional = weighted.reduce((sum, action) => sum + action.notional, 0);
  if (notional <= 0) return null;
  return weighted.reduce(
    (sum, action) => sum + action.notional * action.advantage_pct_points,
    0,
  ) / notional;
}

function descriptiveImpact(action: ScoredDecisionAction) {
  return Math.abs(action.advantage_pct_points) / 100 * action.notional;
}

function niceAxisLimit(actions: ScoredDecisionAction[], deadband: number) {
  const largest = Math.max(
    deadband * 2,
    ...actions.map((action) => Math.abs(action.advantage_pct_points)),
    1,
  );
  const step = largest <= 10 ? 2 : largest <= 25 ? 5 : largest <= 100 ? 10 : 25;
  return Math.ceil(largest / step) * step;
}

function OutcomeLabel({ outcome }: { outcome: DecisionOutcome }) {
  return (
    <span className={`text-xs font-medium ${outcomeStyles[outcome].text}`}>
      {outcomeLabel(outcome)}
    </span>
  );
}

function OutcomeLegend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-calm-muted" aria-label="Outcome legend">
      {(['behind', 'similar', 'ahead'] as const).map((outcome) => (
        <span key={outcome} className="inline-flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${outcomeStyles[outcome].dot}`} aria-hidden="true" />
          {outcomeLabel(outcome)}
        </span>
      ))}
    </div>
  );
}

function ActionAdvantageChart({
  actions,
  deadband,
  benchmarkTicker,
}: {
  actions: ScoredDecisionAction[];
  deadband: number;
  benchmarkTicker: string;
}) {
  if (actions.length === 0) {
    return <p className="text-sm text-calm-muted">No mature scored actions are available.</p>;
  }

  const sortedActions = [...actions].sort((a, b) => descriptiveImpact(b) - descriptiveImpact(a));
  const axisLimit = niceAxisLimit(sortedActions, deadband);
  const deadbandHalfWidth = Math.min(50, (deadband / axisLimit) * 50);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-4 text-xs font-medium text-calm-muted" aria-hidden="true">
          <span>← Behind</span>
          <span>Ahead →</span>
        </div>
        <OutcomeLegend />
      </div>

      <div className="space-y-0" role="list" aria-label="Mature action advantage by date">
        {sortedActions.map((action) => {
          const advantage = action.advantage_pct_points;
          const barWidth = Math.max(0.75, Math.min(50, (Math.abs(advantage) / axisLimit) * 50));
          const ticker = action.ticker ?? 'Unknown ticker';
          const accessibleLabel = [
            `${ticker} action on ${formatDate(action.action_date)}`,
            `${outcomeLabel(action.outcome)} the ${benchmarkTicker} comparison by ${formatPp(advantage)}`,
            `action return ${formatReturn(action.chosen_return_pct)}`,
            `benchmark return ${formatReturn(action.benchmark_return_pct)}`,
            `descriptive impact ${currencyFormatter.format(descriptiveImpact(action))}`,
          ].join('. ');

          return (
            <div
              key={action.action_id}
              className="grid grid-cols-[minmax(0,1fr)_4.75rem] gap-x-3 gap-y-1 border-b border-calm-border/60 py-2.5 sm:grid-cols-[9rem_minmax(0,1fr)_4.75rem] sm:items-center"
              role="listitem"
            >
              <div className="col-span-2 flex min-w-0 items-baseline justify-between gap-2 sm:col-span-1 sm:block">
                <span className="truncate text-sm font-medium">{ticker}</span>
                <time className="text-xs text-calm-muted" dateTime={action.action_date}>
                  {formatDate(action.action_date)}
                </time>
                <span className="block text-xs text-calm-muted">
                  {currencyFormatter.format(descriptiveImpact(action))} effect
                </span>
              </div>

              <div
                className="relative h-6 overflow-hidden rounded bg-calm-bg"
                role="img"
                aria-label={accessibleLabel}
              >
                <span
                  className="absolute inset-y-0 bg-calm-blue/10"
                  style={{
                    left: `${50 - deadbandHalfWidth}%`,
                    width: `${deadbandHalfWidth * 2}%`,
                  }}
                  aria-hidden="true"
                />
                <span
                  className="absolute inset-y-0 left-1/2 w-px bg-calm-muted/60"
                  aria-hidden="true"
                />
                <span
                  className={`absolute top-1/2 h-2 -translate-y-1/2 rounded-sm ${outcomeStyles[action.outcome].bar}`}
                  style={advantage >= 0
                    ? { left: '50%', width: `${barWidth}%` }
                    : { right: '50%', width: `${barWidth}%` }}
                  aria-hidden="true"
                />
              </div>

              <span className={`text-right text-sm font-medium tabular-nums ${outcomeStyles[action.outcome].text}`}>
                {formatPp(advantage)}
              </span>
            </div>
          );
        })}
      </div>

      <div
        className="mt-1 grid grid-cols-[minmax(0,1fr)_4.75rem] gap-x-3 sm:grid-cols-[9rem_minmax(0,1fr)_4.75rem]"
        aria-hidden="true"
      >
        <div className="relative col-span-1 h-5 text-[11px] text-calm-muted sm:col-start-2">
          <span className="absolute left-0">−{axisLimit} pp</span>
          <span className="absolute left-1/2 -translate-x-1/2">0</span>
          <span className="absolute right-0">+{axisLimit} pp</span>
        </div>
      </div>
    </div>
  );
}

function buildMatureYears(
  actions: ScoredDecisionAction[],
  yearBuckets: DecisionQualityYearBucket[],
): MatureYear[] {
  const years = new Set<number>(yearBuckets.map((bucket) => bucket.year));
  actions.forEach((action) => years.add(Number(action.action_date.slice(0, 4))));

  return [...years]
    .sort((a, b) => a - b)
    .map((year) => {
      const yearActions = actions.filter((action) => Number(action.action_date.slice(0, 4)) === year);
      return {
        year,
        actions: yearActions,
        ahead: yearActions.filter((action) => action.outcome === 'ahead').length,
        similar: yearActions.filter((action) => action.outcome === 'similar').length,
        behind: yearActions.filter((action) => action.outcome === 'behind').length,
        weightedAdvantage: weightedAdvantage(yearActions),
      };
    })
    .filter((bucket) => bucket.actions.length > 0);
}

function YearOutcomeBars({ years }: { years: MatureYear[] }) {
  if (years.length === 0) {
    return <p className="text-sm text-calm-muted">No mature years are available.</p>;
  }

  return (
    <div className="space-y-4">
      <OutcomeLegend />
      <div className="space-y-4" role="list" aria-label="Mature action outcomes by year">
        {years.map((year) => {
          const total = year.actions.length;
          const segments = [
            { outcome: 'behind' as const, count: year.behind },
            { outcome: 'similar' as const, count: year.similar },
            { outcome: 'ahead' as const, count: year.ahead },
          ];

          return (
            <div
              key={year.year}
              className="grid grid-cols-1 gap-1.5 sm:grid-cols-[4rem_minmax(0,1fr)_7rem] sm:items-center sm:gap-3"
              role="listitem"
            >
              <div className="flex items-baseline justify-between sm:block">
                <span className="text-sm font-medium">{year.year}</span>
                <span className="text-xs text-calm-muted sm:block">
                  {total} {total === 1 ? 'action' : 'actions'}
                </span>
              </div>
              <div
                className="flex h-7 overflow-hidden rounded bg-calm-bg"
                role="img"
                aria-label={`${year.year}: ${year.behind} behind, ${year.similar} similar, ${year.ahead} ahead among ${total} mature actions`}
              >
                {segments.map((segment) => segment.count > 0 && (
                  <span
                    key={segment.outcome}
                    className={outcomeStyles[segment.outcome].bar}
                    style={{ width: `${(segment.count / total) * 100}%` }}
                    aria-hidden="true"
                  />
                ))}
              </div>
              <span className="text-right text-sm font-medium tabular-nums">
                {formatPp(year.weightedAdvantage)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-calm-muted">
        Bars count mature actions; the right-hand value is each year&apos;s notional-weighted advantage.
      </p>
    </div>
  );
}

function LargestDeparturesTable({
  actions,
  benchmarkTicker,
}: {
  actions: ScoredDecisionAction[];
  benchmarkTicker: string;
}) {
  const departures = actions
    .filter((action) => action.outcome !== 'similar')
    .sort((a, b) => descriptiveImpact(b) - descriptiveImpact(a))
    .slice(0, 8);

  if (departures.length === 0) {
    return <p className="text-sm text-calm-muted">No ahead or behind mature actions are available.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px] text-sm">
        <thead>
          <tr className="border-b border-calm-border text-left text-xs uppercase tracking-wide text-calm-muted">
            <th className="pb-2 pr-4">Outcome</th>
            <th className="pb-2 pr-4">Action</th>
            <th className="pb-2 pr-4">Account</th>
            <th className="pb-2 pr-4 text-right">Action return</th>
            <th className="pb-2 pr-4 text-right">{benchmarkTicker} return</th>
            <th className="pb-2 text-right">Advantage</th>
            <th className="pb-2 text-right">Effect</th>
          </tr>
        </thead>
        <tbody>
          {departures.map((action) => (
            <tr key={action.action_id} className="border-b border-calm-border/60">
              <td className="py-2.5 pr-4">
                <OutcomeLabel outcome={action.outcome} />
              </td>
              <td className="py-2.5 pr-4">
                <span className="font-medium">{action.ticker ?? 'Unknown ticker'}</span>
                <time className="ml-2 text-xs text-calm-muted" dateTime={action.action_date}>
                  {formatDate(action.action_date)}
                </time>
                <span className="block text-xs text-calm-muted">
                  {currencyFormatter.format(action.notional)} notional
                </span>
              </td>
              <td className="py-2.5 pr-4 text-calm-muted">{formatAccount(action.account_key)}</td>
              <td className="py-2.5 pr-4 text-right tabular-nums">
                {formatReturn(action.chosen_return_pct)}
              </td>
              <td className="py-2.5 pr-4 text-right tabular-nums">
                {formatReturn(action.benchmark_return_pct)}
              </td>
              <td className={`py-2.5 pr-4 text-right font-medium tabular-nums ${outcomeStyles[action.outcome].text}`}>
                {formatPp(action.advantage_pct_points)}
              </td>
              <td className="py-2.5 text-right font-medium tabular-nums">
                {currencyFormatter.format(descriptiveImpact(action))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DevelopingActions({
  actions,
  horizonDays,
}: {
  actions: ScoredDecisionAction[];
  horizonDays: number;
}) {
  return (
    <Card>
      <details>
        <summary className="cursor-pointer text-sm font-medium">
          Developing actions ({actions.length})
          <span className="ml-2 font-normal text-calm-muted">
            still building a full {Math.round(horizonDays / 30.4)}-month record
          </span>
        </summary>

        <div className="mt-4 border-t border-calm-border pt-4">
          <p className="mb-4 text-sm text-calm-muted">
            These provisional comparisons are separate from the primary summary, chart, and yearly bars.
          </p>
          {actions.length === 0 ? (
            <p className="text-sm text-calm-muted">No developing actions are currently scored.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-calm-border text-left text-xs uppercase tracking-wide text-calm-muted">
                    <th className="pb-2 pr-4">Action</th>
                    <th className="pb-2 pr-4">Observed window</th>
                    <th className="pb-2 pr-4">Current label</th>
                    <th className="pb-2 text-right">Current advantage</th>
                  </tr>
                </thead>
                <tbody>
                  {[...actions]
                    .sort((a, b) => a.action_date.localeCompare(b.action_date))
                    .map((action) => (
                      <tr key={action.action_id} className="border-b border-calm-border/60">
                        <td className="py-2.5 pr-4">
                          <span className="font-medium">{action.ticker ?? 'Unknown ticker'}</span>
                          <time className="ml-2 text-xs text-calm-muted" dateTime={action.action_date}>
                            {formatDate(action.action_date)}
                          </time>
                        </td>
                        <td className="py-2.5 pr-4 text-calm-muted">
                          {action.observed_days} of {horizonDays} days
                        </td>
                        <td className="py-2.5 pr-4"><OutcomeLabel outcome={action.outcome} /></td>
                        <td className={`py-2.5 text-right font-medium tabular-nums ${outcomeStyles[action.outcome].text}`}>
                          {formatPp(action.advantage_pct_points)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </details>
    </Card>
  );
}

function MethodologyDisclosure({
  benchmark,
  coverage,
  summary,
  primarySummary,
  reconciliation,
  limitations,
  generatedAt,
}: {
  benchmark: DecisionQualityBenchmark;
  coverage: DecisionQualityCoverage;
  summary: DecisionQualitySummary;
  primarySummary: DecisionQualityPrimarySummary;
  reconciliation: DecisionQualityReconciliation;
  limitations: string[];
  generatedAt: string | undefined;
}) {
  return (
    <Card>
      <details>
        <summary className="cursor-pointer text-sm font-medium">
          Methodology, reconciliation, and limitations
        </summary>

        <div className="mt-5 space-y-6 border-t border-calm-border pt-5 text-sm">
          <section aria-labelledby="decision-methodology-heading">
            <h3 id="decision-methodology-heading" className="mb-3 text-xs font-medium uppercase tracking-wide text-calm-muted">
              Methodology
            </h3>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
              <div>
                <dt className="text-calm-muted">Benchmark</dt>
                <dd className="font-medium">{benchmark.ticker} · {benchmark.name}</dd>
              </div>
              <div>
                <dt className="text-calm-muted">Comparison window</dt>
                <dd className="font-medium">{benchmark.horizon_days} days from the first common price date</dd>
              </div>
              <div>
                <dt className="text-calm-muted">Return field</dt>
                <dd className="font-medium capitalize">{benchmark.price_field}</dd>
              </div>
              <div>
                <dt className="text-calm-muted">Similar range</dt>
                <dd className="font-medium">Within ±{benchmark.deadband_pct_points.toFixed(1)} percentage points</dd>
              </div>
              <div>
                <dt className="text-calm-muted">Market data</dt>
                <dd className="font-medium">
                  {benchmark.market_data_source}
                  {benchmark.as_of_date ? ` · through ${formatDate(benchmark.as_of_date)}` : ''}
                </dd>
              </div>
              <div>
                <dt className="text-calm-muted">Generated</dt>
                <dd className="font-medium">{formatDateTime(generatedAt)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-calm-muted">{primarySummary.interpretation}</p>
            <p className="mt-2 text-calm-muted">
              The action-level behind amounts total {currencyFormatter.format(primarySummary.descriptive_opportunity_cost_non_additive)},
              but overlapping comparison windows make that figure non-additive and unsuitable as a portfolio-loss estimate.
            </p>
          </section>

          <section aria-labelledby="decision-coverage-heading">
            <h3 id="decision-coverage-heading" className="mb-3 text-xs font-medium uppercase tracking-wide text-calm-muted">
              Ledger coverage
            </h3>
            <p>
              {coverage.source_files.toLocaleString()} source files produced {coverage.ledger_transactions.toLocaleString()} ledger rows
              from {formatDate(coverage.date_start)} through {formatDate(coverage.date_end)}. Of {coverage.decision_rows.toLocaleString()}
              decision rows, {summary.scored_actions.toLocaleString()} were scored; {summary.excluded_actions.toLocaleString()} were excluded,
              {' '}{summary.missing_price_actions.toLocaleString()} lacked comparable prices, and {summary.duplicate_actions.toLocaleString()} were duplicates.
            </p>
          </section>

          <section aria-labelledby="decision-reconciliation-heading">
            <h3 id="decision-reconciliation-heading" className="mb-3 text-xs font-medium uppercase tracking-wide text-calm-muted">
              Assets spreadsheet reconciliation
            </h3>
            {reconciliation.assets_sheet_available ? (
              <div className="space-y-2">
                <p>{reconciliation.interpretation}</p>
                <p className="text-calm-muted">
                  {reconciliation.snapshot_rows.toLocaleString()} snapshot rows and {reconciliation.action_notes.toLocaleString()} action notes were retained.
                  {' '}{reconciliation.date_symbol_direction_matches_to_pdf_ledger.toLocaleString()} of {reconciliation.dated_completed_notes.toLocaleString()} dated completed notes
                  matched a primary-ledger row on date, ticker, and direction.
                </p>
                {reconciliation.assets_sheet_source_modified_time && (
                  <p className="text-xs text-calm-muted">
                    Secondary source last modified {formatDateTime(reconciliation.assets_sheet_source_modified_time)}.
                  </p>
                )}
                {(reconciliation.symbols_only_in_sheet.length > 0 || reconciliation.symbols_only_in_pdf_ledgers.length > 0) && (
                  <dl className="grid grid-cols-1 gap-3 pt-1 sm:grid-cols-2">
                    <div>
                      <dt className="text-calm-muted">Symbols only in spreadsheet</dt>
                      <dd className="font-medium">{reconciliation.symbols_only_in_sheet.join(', ') || 'None'}</dd>
                    </div>
                    <div>
                      <dt className="text-calm-muted">Symbols only in PDF ledgers</dt>
                      <dd className="font-medium">{reconciliation.symbols_only_in_pdf_ledgers.join(', ') || 'None'}</dd>
                    </div>
                  </dl>
                )}
              </div>
            ) : (
              <p className="text-calm-muted">The Assets spreadsheet was not available for secondary reconciliation.</p>
            )}
          </section>

          <section aria-labelledby="decision-limitations-heading">
            <h3 id="decision-limitations-heading" className="mb-3 text-xs font-medium uppercase tracking-wide text-calm-muted">
              Limitations
            </h3>
            <ul className="list-disc space-y-2 pl-5 text-calm-muted">
              {limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
          </section>
        </div>
      </details>
    </Card>
  );
}

export function DecisionQualityPage() {
  const { data, loading, error, refetch } = useApi<DecisionQualityResponse>('/decisions/quality');

  if (loading && !data) {
    return (
      <div className="space-y-6" aria-busy="true">
        <h2 className="text-2xl font-semibold tracking-tight">Decisions</h2>
        <Card>
          <p className="text-sm text-calm-muted" role="status">Loading decision analysis…</p>
        </Card>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold tracking-tight">Decisions</h2>
        <Card>
          <div role="alert">
            <h3 className="font-medium">Decision analysis could not be loaded</h3>
            <p className="mt-1 text-sm text-calm-muted">{error}</p>
            <Button className="mt-4" variant="secondary" onClick={refetch}>Try again</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!data?.available) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold tracking-tight">Decisions</h2>
        <Card>
          <h3 className="font-medium">Decision analysis is not available yet</h3>
          <p className="mt-1 text-sm text-calm-muted">
            {data?.message ?? 'The private finance import needs to generate decision-quality data with benchmark prices.'}
          </p>
          <Button className="mt-4" variant="secondary" onClick={refetch}>Check again</Button>
        </Card>
      </div>
    );
  }

  const {
    benchmark,
    coverage,
    primary_summary: primarySummary,
    summary,
    reconciliation,
  } = data;

  if (!benchmark || !coverage || !primarySummary || !summary || !reconciliation || !data.actions) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold tracking-tight">Decisions</h2>
        <Card>
          <div role="alert">
            <h3 className="font-medium">Decision analysis is incomplete</h3>
            <p className="mt-1 text-sm text-calm-muted">
              The generated private artifact is missing fields needed by this view.
            </p>
            <Button className="mt-4" variant="secondary" onClick={refetch}>Check again</Button>
          </div>
        </Card>
      </div>
    );
  }

  const scoredActions = data.actions.filter(isScoredAction);
  const matureActions = scoredActions.filter((action) => action.maturity === 'mature');
  const developingActions = scoredActions.filter((action) => action.maturity === 'developing');
  const matureCounts = {
    ahead: matureActions.filter((action) => action.outcome === 'ahead').length,
    similar: matureActions.filter((action) => action.outcome === 'similar').length,
    behind: matureActions.filter((action) => action.outcome === 'behind').length,
  };
  const scorability = coverage.buy_like_candidate_rows > 0
    ? Math.round((summary.scored_actions / coverage.buy_like_candidate_rows) * 100)
    : 0;
  const matureYears = buildMatureYears(matureActions, data.year_buckets ?? []);
  const majorActions = matureActions
    .filter((action) => action.outcome !== 'similar')
    .sort((a, b) => descriptiveImpact(b) - descriptiveImpact(a))
    .slice(0, 10);
  const summaryOutcome = primarySummary.weighted_outcome;

  return (
    <div className="space-y-8 pb-8">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight">Decisions</h2>
        <p className="mt-2 max-w-3xl text-sm text-calm-muted">
          A regret-style comparison of mature buy-like actions with {benchmark.ticker} ({benchmark.name}) over the same{' '}
          {benchmark.horizon_days}-day adjusted-close window. Advantage is the action return minus the benchmark return;
          results within ±{benchmark.deadband_pct_points.toFixed(1)} percentage points are labeled similar.
        </p>
        <p className="mt-1 text-xs text-calm-muted">
          Mature actions are the primary view. Developing actions appear separately and do not affect the primary summary.
        </p>
      </header>

      {error && (
        <div className="rounded bg-calm-amber/10 px-3 py-2 text-sm text-calm-text" role="alert">
          Refresh failed; showing the most recently loaded analysis.
        </div>
      )}

      <section aria-label="Decision summary" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="h-full">
          <p className="mb-1 text-xs uppercase tracking-wide text-calm-muted">12-month weighted advantage</p>
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <p className="text-xl font-medium tabular-nums">
              {formatPp(primarySummary.weighted_advantage_pct_points)}
            </p>
            {summaryOutcome && <OutcomeLabel outcome={summaryOutcome} />}
          </div>
          <p className="mt-2 text-xs text-calm-muted">
            {primarySummary.mature_actions.toLocaleString()} mature actions · notional-weighted vs {benchmark.ticker}
          </p>
        </Card>

        <Card className="h-full">
          <p className="mb-2 text-xs uppercase tracking-wide text-calm-muted">Mature action outcome mix</p>
          <p className="text-lg font-medium tabular-nums">
            {matureCounts.ahead} ahead · {matureCounts.similar} similar · {matureCounts.behind} behind
          </p>
          <div
            className="mt-3 flex h-2 overflow-hidden rounded bg-calm-bg"
            role="img"
            aria-label={`${matureCounts.ahead} ahead, ${matureCounts.similar} similar, and ${matureCounts.behind} behind among mature actions`}
          >
            {(['behind', 'similar', 'ahead'] as const).map((outcome) => {
              const count = matureCounts[outcome];
              return count > 0 ? (
                <span
                  key={outcome}
                  className={outcomeStyles[outcome].bar}
                  style={{ width: `${(count / Math.max(1, matureActions.length)) * 100}%` }}
                  aria-hidden="true"
                />
              ) : null;
            })}
          </div>
        </Card>

        <Card className="h-full">
          <p className="mb-1 text-xs uppercase tracking-wide text-calm-muted">Buy-like price coverage</p>
          <p className="text-xl font-medium tabular-nums">
            {summary.scored_actions.toLocaleString()} of {coverage.buy_like_candidate_rows.toLocaleString()}
          </p>
          <p className="mt-2 text-xs text-calm-muted">
            {scorability}% of candidate rows scored · {primarySummary.developing_actions.toLocaleString()} still developing
          </p>
        </Card>
      </section>

      <Card>
        <div className="mb-5">
          <h3 className="font-medium">Largest mature effects</h3>
          <p className="mt-1 text-sm text-calm-muted">
            Top {majorActions.length} actions by absolute descriptive dollar effect. Actions inside the
            {' '}±{benchmark.deadband_pct_points.toFixed(1)} pp similar range are omitted.
          </p>
        </div>
        <ActionAdvantageChart
          actions={majorActions}
          deadband={benchmark.deadband_pct_points}
          benchmarkTicker={benchmark.ticker}
        />
      </Card>

      <Card>
        <div className="mb-5">
          <h3 className="font-medium">Mature outcomes by action year</h3>
          <p className="mt-1 text-sm text-calm-muted">Counts and weighted advantage use mature actions only.</p>
        </div>
        <YearOutcomeBars years={matureYears} />
      </Card>

      <Card>
        <div className="mb-4">
          <h3 className="font-medium">Major effects detail</h3>
          <p className="mt-1 text-sm text-calm-muted">
            Ranked by absolute advantage multiplied by action notional. These overlapping effects are
            descriptive and cannot be added into a portfolio gain or loss.
          </p>
        </div>
        <LargestDeparturesTable actions={matureActions} benchmarkTicker={benchmark.ticker} />
      </Card>

      <DevelopingActions actions={developingActions} horizonDays={benchmark.horizon_days} />

      <MethodologyDisclosure
        benchmark={benchmark}
        coverage={coverage}
        summary={summary}
        primarySummary={primarySummary}
        reconciliation={reconciliation}
        limitations={data.limitations ?? []}
        generatedAt={data.generated_at}
      />
    </div>
  );
}
