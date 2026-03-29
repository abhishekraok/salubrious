from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# --- Auth ---
class AuthConfigOut(BaseModel):
    oauth_enabled: bool
    google_client_id: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    token: str
    user: "UserProfileOut"


# --- User ---
class UserProfileOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    currency: str

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None


# --- Settings ---
class UserSettingsOut(BaseModel):
    id: int
    hide_performance: bool
    show_values_mode: str
    cooldown_hours: int
    cooldown_enabled: bool
    require_journal_for_override: bool
    check_limit_days: Optional[int]

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    hide_performance: Optional[bool] = None
    show_values_mode: Optional[str] = None
    cooldown_hours: Optional[int] = None
    cooldown_enabled: Optional[bool] = None
    require_journal_for_override: Optional[bool] = None
    check_limit_days: Optional[int] = None


# --- Policy ---
class InvestmentPolicyOut(BaseModel):
    id: int
    name: str
    objective_text: str
    review_cadence: str
    rebalance_method: str
    use_cash_flows_first: bool
    avoid_taxable_sales: bool
    hard_rebalance_only_at_review: bool
    baseline_annual_spending: float
    comfortable_annual_spending: float
    emergency_annual_spending: float
    safe_asset_runway_years_target: float
    minimum_cash_reserve: float
    expected_years_remaining: Optional[int]
    expected_years_earning: Optional[int]
    expected_after_tax_salary: Optional[float]
    withdrawal_rate_pct: float
    targeting_mode: str
    target_equity_pct: Optional[float]
    target_international_pct: Optional[float]
    target_value_tilted_pct: Optional[float]
    target_small_cap_pct: Optional[float]
    things_i_do_not_do: Optional[str]
    next_review_date: Optional[date]
    last_review_date: Optional[date]

    model_config = {"from_attributes": True}


class InvestmentPolicyUpdate(BaseModel):
    name: Optional[str] = None
    objective_text: Optional[str] = None
    review_cadence: Optional[str] = None
    rebalance_method: Optional[str] = None
    use_cash_flows_first: Optional[bool] = None
    avoid_taxable_sales: Optional[bool] = None
    hard_rebalance_only_at_review: Optional[bool] = None
    baseline_annual_spending: Optional[float] = None
    comfortable_annual_spending: Optional[float] = None
    emergency_annual_spending: Optional[float] = None
    safe_asset_runway_years_target: Optional[float] = None
    minimum_cash_reserve: Optional[float] = None
    expected_years_remaining: Optional[int] = None
    expected_years_earning: Optional[int] = None
    expected_after_tax_salary: Optional[float] = None
    withdrawal_rate_pct: Optional[float] = None
    targeting_mode: Optional[str] = None
    target_equity_pct: Optional[float] = None
    target_international_pct: Optional[float] = None
    target_value_tilted_pct: Optional[float] = None
    target_small_cap_pct: Optional[float] = None
    things_i_do_not_do: Optional[str] = None
    next_review_date: Optional[date] = None
    last_review_date: Optional[date] = None


# --- Sleeve ---
class PortfolioSleeveOut(BaseModel):
    id: int
    policy_id: int
    ticker: str
    label: str
    target_percent: float
    asset_class: str
    geography: Optional[str]
    region_us_pct: float
    region_developed_pct: float
    region_emerging_pct: float
    factor_value: Optional[str]
    factor_size: Optional[str]
    preferred_account_type: Optional[str]
    is_safe_asset: bool
    is_cash_like: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class PortfolioSleeveCreate(BaseModel):
    ticker: str
    label: str
    target_percent: float
    asset_class: str
    geography: Optional[str] = None
    region_us_pct: float = 0.0
    region_developed_pct: float = 0.0
    region_emerging_pct: float = 0.0
    factor_value: Optional[str] = None
    factor_size: Optional[str] = None
    preferred_account_type: Optional[str] = None
    is_safe_asset: bool = False
    is_cash_like: bool = False
    notes: Optional[str] = None


class PortfolioSleeveUpdate(BaseModel):
    ticker: Optional[str] = None
    label: Optional[str] = None
    target_percent: Optional[float] = None
    asset_class: Optional[str] = None
    geography: Optional[str] = None
    region_us_pct: Optional[float] = None
    region_developed_pct: Optional[float] = None
    region_emerging_pct: Optional[float] = None
    factor_value: Optional[str] = None
    factor_size: Optional[str] = None
    preferred_account_type: Optional[str] = None
    is_safe_asset: Optional[bool] = None
    is_cash_like: Optional[bool] = None
    notes: Optional[str] = None


# --- Account ---
class AccountOut(BaseModel):
    id: int
    institution_name: str
    account_name: str
    account_type: str
    is_tax_advantaged: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class AccountCreate(BaseModel):
    institution_name: str
    account_name: str
    account_type: str
    is_tax_advantaged: bool = False
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    institution_name: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    is_tax_advantaged: Optional[bool] = None
    notes: Optional[str] = None


# --- Holding ---
class HoldingOut(BaseModel):
    id: int
    account_id: int
    ticker: str
    quantity: float
    price: float
    market_value: float
    as_of_date: date

    model_config = {"from_attributes": True}


class HoldingCreate(BaseModel):
    ticker: str
    quantity: float
    price: float
    as_of_date: Optional[date] = None


class HoldingUpdate(BaseModel):
    ticker: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    as_of_date: Optional[date] = None


# --- Contribution ---
class ContributionOut(BaseModel):
    id: int
    account_id: int
    amount: float
    contribution_date: date
    note: Optional[str]

    model_config = {"from_attributes": True}


class ContributionCreate(BaseModel):
    account_id: int
    amount: float
    contribution_date: Optional[date] = None
    note: Optional[str] = None


# --- Review ---
class ReviewEntryOut(BaseModel):
    id: int
    policy_id: int
    review_date: date
    summary: str
    life_change_flag: bool
    allocation_changed_flag: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class ReviewEntryCreate(BaseModel):
    review_date: Optional[date] = None
    summary: str
    life_change_flag: bool = False
    allocation_changed_flag: bool = False
    notes: Optional[str] = None


# --- Journal ---
class JournalEntryOut(BaseModel):
    id: int
    user_id: int
    entry_date: date
    action_type: str
    reason_category: str
    explanation: str
    confidence_score: Optional[int]
    follow_up_date: Optional[date]

    model_config = {"from_attributes": True}


class JournalEntryCreate(BaseModel):
    entry_date: Optional[date] = None
    action_type: str
    reason_category: str
    explanation: str
    confidence_score: Optional[int] = None
    follow_up_date: Optional[date] = None


# --- Crash Plan ---
class CrashPlanTriggerOut(BaseModel):
    id: int
    policy_id: int
    trigger_name: str
    trigger_type: str
    threshold_value: float
    source_ticker: str
    destination_tickers: str
    action_amount_type: str
    action_amount_value: float
    enabled: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class CrashPlanTriggerCreate(BaseModel):
    trigger_name: str
    trigger_type: str
    threshold_value: float
    source_ticker: str
    destination_tickers: str
    action_amount_type: str
    action_amount_value: float
    enabled: bool = True
    notes: Optional[str] = None
