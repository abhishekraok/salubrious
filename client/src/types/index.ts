export interface UserProfile {
  id: number;
  name: string;
  currency: string;
}

export interface UserSettings {
  id: number;
  hide_performance: boolean;
  show_values_mode: string;
  cooldown_hours: number;
  cooldown_enabled: boolean;
  require_journal_for_override: boolean;
  check_limit_days: number | null;
}

export interface InvestmentPolicy {
  id: number;
  name: string;
  objective_text: string;
  rebalance_method: string;
  use_cash_flows_first: boolean;
  avoid_taxable_sales: boolean;
  hard_rebalance_only_at_review: boolean;
  baseline_annual_spending: number;
  comfortable_annual_spending: number;
  emergency_annual_spending: number;
  safe_asset_runway_years_target: number;
  minimum_cash_reserve: number;
  targeting_mode: string;
  target_equity_pct: number | null;
  target_international_pct: number | null;
  target_value_tilted_pct: number | null;
  target_small_cap_pct: number | null;
  expected_years_remaining: number | null;
  expected_years_earning: number | null;
  expected_after_tax_salary: number | null;
  withdrawal_rate_pct: number;
}

export interface PortfolioSleeve {
  id: number;
  policy_id: number;
  ticker: string;
  label: string;
  target_percent: number;
  asset_class: string;
  geography: string | null;
  region_us_pct: number;
  region_developed_pct: number;
  region_emerging_pct: number;
  factor_value: string | null;
  factor_size: string | null;
  preferred_account_type: string | null;
  is_safe_asset: boolean;
  is_cash_like: boolean;
  notes: string | null;
}

export interface Account {
  id: number;
  institution_name: string;
  account_name: string;
  account_type: string;
  is_tax_advantaged: boolean;
  notes: string | null;
}

export interface Holding {
  id: number;
  account_id: number;
  ticker: string;
  quantity: number;
  price: number;
  market_value: number;
  as_of_date: string;
}


export interface SleeveAllocation {
  ticker: string;
  label: string;
  current_value: number;
  current_percent: number;
  target_percent: number;
  drift_pp: number;
  soft_band: number;
  hard_band: number;
  status: 'ok' | 'watch' | 'action_needed';
}

export interface AllocationResult {
  total_value: number;
  sleeves: SleeveAllocation[];
  sleeves_outside_soft: number;
  sleeves_outside_hard: number;
}

export interface ActionItem {
  action: string;
  ticker: string;
  amount: number;
  source_ticker: string | null;
  rationale: string;
}

export interface RebalanceSuggestion {
  headline: string;
  action_items: ActionItem[];
  rationale: string;
  urgency: string;
}

export interface TodayRecommendation {
  headline: string;
  explanation: string;
  status: 'calm' | 'watch' | 'action';
  summary_cards: { label: string; value: string; status: string }[];
  active_issues: string[];
}

export interface SpendingGuidance {
  total_portfolio_value: number;
  withdrawal_rate_pct: number;
  recommended_annual_spending: number;
  current_baseline_spending: number;
  spending_status: 'low' | 'appropriate' | 'high';
  future_earnings_present_value: number;
  effective_wealth: number;
  effective_recommended_spending: number;
  years_remaining: number | null;
  years_earning: number | null;
  after_tax_salary: number | null;
}

export interface SimulationResult {
  years: number[];
  p5: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
  ruin_probability: number;
  ruin_by_year: number[];
  spending_floor: number;
  spending_recommended: number;
  spending_ceiling: number;
}

export interface SpendingRunway {
  safe_asset_total: number;
  cash_like_total: number;
  baseline_runway_years: number;
  comfortable_runway_years: number;
  emergency_runway_years: number;
  cash_runway_years: number;
  funded_status: string;
  above_minimum_reserve_by: number;
}

export type DecisionOutcome = 'ahead' | 'similar' | 'behind';
export type DecisionMaturity = 'mature' | 'developing';
export type DecisionScoreStatus = 'scored' | 'excluded' | 'missing_prices' | 'duplicate';

export interface DecisionQualityBenchmark {
  ticker: string;
  name: string;
  horizon_days: number;
  deadband_pct_points: number;
  price_field: string;
  market_data_source: string;
  as_of_date: string;
}

export interface DecisionQualityCoverage {
  source_files: number;
  ledger_transactions: number;
  performance_periods: number;
  decision_rows: number;
  buy_like_candidate_rows: number;
  automatic_or_cash_rows_not_treated_as_decisions: number;
  date_start: string;
  date_end: string;
}

export interface DecisionQualityPrimarySummary {
  basis: string;
  mature_actions: number;
  developing_actions: number;
  weighted_advantage_pct_points: number | null;
  weighted_outcome: DecisionOutcome | null;
  descriptive_opportunity_cost_non_additive: number;
  interpretation: string;
}

export interface DecisionQualitySummary {
  benchmark_ticker: string;
  horizon_days: number;
  deadband_pct_points: number;
  total_actions: number;
  scored_actions: number;
  mature_actions: number;
  developing_actions: number;
  ahead_actions: number;
  similar_actions: number;
  behind_actions: number;
  excluded_actions: number;
  missing_price_actions: number;
  duplicate_actions: number;
  scored_notional: number;
  weighted_advantage_pct_points: number | null;
  weighted_outcome: DecisionOutcome | null;
  interpretation: string;
}

export interface DecisionQualityYearBucket {
  year: number;
  actions: number;
  mature: number;
  developing: number;
  ahead: number;
  similar: number;
  behind: number;
  weighted_advantage_pct_points: number | null;
}

export interface DecisionQualityAction {
  action_id: string;
  action_date: string;
  action_type: string;
  ticker: string | null;
  notional: number;
  benchmark_ticker: string;
  score_status: DecisionScoreStatus;
  reason: string | null;
  maturity: DecisionMaturity | null;
  outcome: DecisionOutcome | null;
  entry_date: string | null;
  evaluation_date: string | null;
  horizon_date: string | null;
  observed_days: number | null;
  chosen_return_pct: number | null;
  benchmark_return_pct: number | null;
  advantage_pct_points: number | null;
  opportunity_cost: number | null;
  institution?: string;
  account_key?: string;
  security_name?: string;
  source_file?: string;
  parse_confidence?: string;
  evidence_role?: string;
}

export interface DecisionQualityReconciliation {
  assets_sheet_available: boolean;
  assets_sheet_evidence_role: string | null;
  assets_sheet_source_modified_time?: string | null;
  snapshot_rows: number;
  action_notes: number;
  reported_completed_notes: number;
  dated_completed_notes: number;
  date_symbol_direction_matches_to_pdf_ledger: number;
  dated_completed_notes_without_date_symbol_direction_match: number;
  symbols_only_in_sheet: string[];
  symbols_only_in_pdf_ledgers: string[];
  interpretation: string;
}

export interface DecisionQualityResponse {
  schema_version: number;
  available: boolean;
  message?: string;
  generated_at?: string;
  benchmark?: DecisionQualityBenchmark;
  coverage?: DecisionQualityCoverage;
  primary_summary?: DecisionQualityPrimarySummary;
  summary?: DecisionQualitySummary;
  year_buckets?: DecisionQualityYearBucket[];
  actions?: DecisionQualityAction[];
  reconciliation?: DecisionQualityReconciliation;
  limitations?: string[];
}
