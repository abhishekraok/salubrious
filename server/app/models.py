from datetime import date, datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user")
    policies: Mapped[list["InvestmentPolicy"]] = relationship(back_populates="user")
    accounts: Mapped[list["Account"]] = relationship(back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    hide_performance: Mapped[bool] = mapped_column(default=True)
    show_values_mode: Mapped[str] = mapped_column(String(20), default="both")
    cooldown_hours: Mapped[int] = mapped_column(default=24)
    cooldown_enabled: Mapped[bool] = mapped_column(default=False)
    require_journal_for_override: Mapped[bool] = mapped_column(default=True)
    check_limit_days: Mapped[Optional[int]] = mapped_column(nullable=True)

    user: Mapped["UserProfile"] = relationship(back_populates="settings")


class InvestmentPolicy(Base):
    __tablename__ = "investment_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(200))
    objective_text: Mapped[str] = mapped_column(
        Text,
        default="Maximize long-term expected consumption utility while minimizing "
        "unnecessary cognitive load and behavioral mistakes.",
    )
    review_cadence: Mapped[str] = mapped_column(String(20), default="annual")
    rebalance_method: Mapped[str] = mapped_column(String(20), default="hybrid")
    use_cash_flows_first: Mapped[bool] = mapped_column(default=True)
    avoid_taxable_sales: Mapped[bool] = mapped_column(default=True)
    hard_rebalance_only_at_review: Mapped[bool] = mapped_column(default=True)
    baseline_annual_spending: Mapped[float] = mapped_column(default=0.0)
    comfortable_annual_spending: Mapped[float] = mapped_column(default=0.0)
    emergency_annual_spending: Mapped[float] = mapped_column(default=0.0)
    safe_asset_runway_years_target: Mapped[float] = mapped_column(default=4.0)
    minimum_cash_reserve: Mapped[float] = mapped_column(default=0.0)
    targeting_mode: Mapped[str] = mapped_column(String(20), default="fund")
    target_equity_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_international_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_value_tilted_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_small_cap_pct: Mapped[Optional[float]] = mapped_column(nullable=True)
    things_i_do_not_do: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_review_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    last_review_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    user: Mapped["UserProfile"] = relationship(back_populates="policies")
    sleeves: Mapped[list["PortfolioSleeve"]] = relationship(back_populates="policy")
    crash_plan_triggers: Mapped[list["CrashPlanTrigger"]] = relationship(back_populates="policy")
    reviews: Mapped[list["ReviewEntry"]] = relationship(back_populates="policy")


class PortfolioSleeve(Base):
    __tablename__ = "portfolio_sleeves"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("investment_policies.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    label: Mapped[str] = mapped_column(String(100))
    target_percent: Mapped[float]
    asset_class: Mapped[str] = mapped_column(String(50))
    geography: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    region_us_pct: Mapped[float] = mapped_column(default=0.0)
    region_developed_pct: Mapped[float] = mapped_column(default=0.0)
    region_emerging_pct: Mapped[float] = mapped_column(default=0.0)
    factor_value: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    factor_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    preferred_account_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_safe_asset: Mapped[bool] = mapped_column(default=False)
    is_cash_like: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    policy: Mapped["InvestmentPolicy"] = relationship(back_populates="sleeves")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    institution_name: Mapped[str] = mapped_column(String(100))
    account_name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(50))
    is_tax_advantaged: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["UserProfile"] = relationship(back_populates="accounts")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="account")
    contributions: Mapped[list["Contribution"]] = relationship(back_populates="account")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[float]
    price: Mapped[float]
    market_value: Mapped[float]
    as_of_date: Mapped[date]

    account: Mapped["Account"] = relationship(back_populates="holdings")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    total_value: Mapped[float]
    total_safe_assets: Mapped[float]
    total_equities: Mapped[float]
    as_of_date: Mapped[date]
    sleeve_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[float]
    contribution_date: Mapped[date]
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="contributions")


class ReviewEntry(Base):
    __tablename__ = "review_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("investment_policies.id"))
    review_date: Mapped[date]
    summary: Mapped[str] = mapped_column(Text)
    life_change_flag: Mapped[bool] = mapped_column(default=False)
    allocation_changed_flag: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    policy: Mapped["InvestmentPolicy"] = relationship(back_populates="reviews")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    entry_date: Mapped[date]
    action_type: Mapped[str] = mapped_column(String(100))
    reason_category: Mapped[str] = mapped_column(String(50))
    explanation: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(nullable=True)


class CrashPlanTrigger(Base):
    __tablename__ = "crash_plan_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("investment_policies.id"))
    trigger_name: Mapped[str] = mapped_column(String(100))
    trigger_type: Mapped[str] = mapped_column(String(50))
    threshold_value: Mapped[float]
    source_ticker: Mapped[str] = mapped_column(String(10))
    destination_tickers: Mapped[str] = mapped_column(String(200))
    action_amount_type: Mapped[str] = mapped_column(String(20))
    action_amount_value: Mapped[float]
    enabled: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    policy: Mapped["InvestmentPolicy"] = relationship(back_populates="crash_plan_triggers")
