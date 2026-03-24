"""Seed the database with example data (Bernstein 3-fund portfolio)."""

from datetime import date, timedelta

from .database import SessionLocal, engine
from .models import (
    Account,
    Base,
    Holding,
    InvestmentPolicy,
    PortfolioSleeve,
    UserProfile,
    UserSettings,
)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Skip if already seeded
    if db.query(UserProfile).first():
        print("Database already seeded.")
        db.close()
        return

    # User
    user = UserProfile(name="Default User", currency="USD")
    db.add(user)
    db.flush()

    # Settings
    settings = UserSettings(user_id=user.id)
    db.add(settings)

    # Policy — simple 3-fund example
    policy = InvestmentPolicy(
        user_id=user.id,
        name="Core Investment Policy",
        objective_text=(
            "Grow wealth steadily over the long term while keeping "
            "costs low and decisions simple."
        ),
        review_cadence="annual",
        rebalance_method="hybrid",
        use_cash_flows_first=True,
        avoid_taxable_sales=True,
        hard_rebalance_only_at_review=True,
        baseline_annual_spending=40_000,
        comfortable_annual_spending=50_000,
        emergency_annual_spending=30_000,
        safe_asset_runway_years_target=4.0,
        minimum_cash_reserve=10_000,
        targeting_mode="fund",
        target_equity_pct=67,
        target_international_pct=50,
        target_value_tilted_pct=0,
        target_small_cap_pct=0,
        things_i_do_not_do=(
            '["I do not react to headlines.",'
            '"I do not sell equities because of fear.",'
            '"I do not change asset allocation without a life change or scheduled review."]'
        ),
        next_review_date=date.today() + timedelta(days=180),
        last_review_date=date.today() - timedelta(days=185),
    )
    db.add(policy)
    db.flush()

    # Bernstein 3-fund portfolio: equal thirds
    # (ticker, label, target%, asset_class, geo, is_safe, is_cash, us%, dev%, em%, f_value, f_size)
    sleeves_data = [
        ("BND", "Vanguard Total Bond Market", 33, "nominal_bond", "us", True, False, 100, 0, 0, None, None),
        ("VTI", "Vanguard Total US Stock", 34, "equity", "us", False, False, 100, 0, 0, "blend", "blend"),
        ("VXUS", "Vanguard Total Intl Stock", 33, "equity", "international", False, False, 0, 80, 20, "blend", "blend"),
    ]

    for ticker, label, target, asset_class, geo, is_safe, is_cash, us, dev, em, f_val, f_size in sleeves_data:
        db.add(PortfolioSleeve(
            policy_id=policy.id,
            ticker=ticker,
            label=label,
            target_percent=target,
            asset_class=asset_class,
            geography=geo,
            is_safe_asset=is_safe,
            is_cash_like=is_cash,
            region_us_pct=us,
            region_developed_pct=dev,
            region_emerging_pct=em,
            factor_value=f_val,
            factor_size=f_size,
        ))

    # Sample brokerage account (~$300K portfolio)
    account = Account(
        user_id=user.id,
        institution_name="Vanguard",
        account_name="Taxable Brokerage",
        account_type="taxable",
        is_tax_advantaged=False,
    )
    db.add(account)
    db.flush()

    holdings_data = [
        ("BND", 1350, 73.00),   # ~$98,550
        ("VTI", 370, 280.00),   # ~$103,600
        ("VXUS", 1700, 58.00),  # ~$98,600
    ]

    for ticker, qty, price in holdings_data:
        db.add(Holding(
            account_id=account.id,
            ticker=ticker,
            quantity=qty,
            price=price,
            market_value=qty * price,
            as_of_date=date.today(),
        ))

    db.commit()
    db.close()
    print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
