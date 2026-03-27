"""Full profile JSON export/import for data portability."""

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    Account,
    Contribution,
    CrashPlanTrigger,
    Holding,
    InvestmentPolicy,
    JournalEntry,
    PortfolioSleeve,
    ReviewEntry,
    UserProfile,
    UserSettings,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])

EXPORT_VERSION = 1


def _serialize_date(obj):
    """JSON serializer for date/datetime objects."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@router.get("/export")
def export_profile(db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    """Export complete user profile as JSON."""
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()

    sleeves = []
    crash_plan_triggers = []
    reviews = []
    if policy:
        sleeves = db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
        crash_plan_triggers = db.query(CrashPlanTrigger).filter(CrashPlanTrigger.policy_id == policy.id).all()
        reviews = db.query(ReviewEntry).filter(ReviewEntry.policy_id == policy.id).all()

    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all() if account_ids else []
    contributions = db.query(Contribution).filter(Contribution.account_id.in_(account_ids)).all() if account_ids else []
    journal_entries = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).all()

    export_data = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "user": {
            "name": user.name,
            "currency": user.currency,
        },
        "settings": {
            "hide_performance": settings.hide_performance,
            "show_values_mode": settings.show_values_mode,
            "cooldown_hours": settings.cooldown_hours,
            "cooldown_enabled": settings.cooldown_enabled,
            "require_journal_for_override": settings.require_journal_for_override,
            "check_limit_days": settings.check_limit_days,
        } if settings else None,
        "policy": {
            "name": policy.name,
            "objective_text": policy.objective_text,
            "review_cadence": policy.review_cadence,
            "rebalance_method": policy.rebalance_method,
            "use_cash_flows_first": policy.use_cash_flows_first,
            "avoid_taxable_sales": policy.avoid_taxable_sales,
            "hard_rebalance_only_at_review": policy.hard_rebalance_only_at_review,
            "baseline_annual_spending": policy.baseline_annual_spending,
            "comfortable_annual_spending": policy.comfortable_annual_spending,
            "emergency_annual_spending": policy.emergency_annual_spending,
            "safe_asset_runway_years_target": policy.safe_asset_runway_years_target,
            "minimum_cash_reserve": policy.minimum_cash_reserve,
            "targeting_mode": policy.targeting_mode,
            "target_equity_pct": policy.target_equity_pct,
            "target_international_pct": policy.target_international_pct,
            "target_value_tilted_pct": policy.target_value_tilted_pct,
            "target_small_cap_pct": policy.target_small_cap_pct,
            "things_i_do_not_do": policy.things_i_do_not_do,
            "next_review_date": policy.next_review_date,
            "last_review_date": policy.last_review_date,
        } if policy else None,
        "sleeves": [
            {
                "ticker": s.ticker,
                "label": s.label,
                "target_percent": s.target_percent,
                "asset_class": s.asset_class,
                "geography": s.geography,
                "region_us_pct": s.region_us_pct,
                "region_developed_pct": s.region_developed_pct,
                "region_emerging_pct": s.region_emerging_pct,
                "factor_value": s.factor_value,
                "factor_size": s.factor_size,
                "preferred_account_type": s.preferred_account_type,
                "is_safe_asset": s.is_safe_asset,
                "is_cash_like": s.is_cash_like,
                "notes": s.notes,
            }
            for s in sleeves
        ],
        "accounts": [
            {
                "institution_name": a.institution_name,
                "account_name": a.account_name,
                "account_type": a.account_type,
                "is_tax_advantaged": a.is_tax_advantaged,
                "notes": a.notes,
                "holdings": [
                    {
                        "ticker": h.ticker,
                        "quantity": h.quantity,
                        "price": h.price,
                        "market_value": h.market_value,
                        "as_of_date": h.as_of_date,
                    }
                    for h in holdings
                    if h.account_id == a.id
                ],
                "contributions": [
                    {
                        "amount": c.amount,
                        "contribution_date": c.contribution_date,
                        "note": c.note,
                    }
                    for c in contributions
                    if c.account_id == a.id
                ],
            }
            for a in accounts
        ],
        "reviews": [
            {
                "review_date": r.review_date,
                "summary": r.summary,
                "life_change_flag": r.life_change_flag,
                "allocation_changed_flag": r.allocation_changed_flag,
                "notes": r.notes,
            }
            for r in reviews
        ],
        "journal_entries": [
            {
                "entry_date": j.entry_date,
                "action_type": j.action_type,
                "reason_category": j.reason_category,
                "explanation": j.explanation,
                "confidence_score": j.confidence_score,
                "follow_up_date": j.follow_up_date,
            }
            for j in journal_entries
        ],
        "crash_plan_triggers": [
            {
                "trigger_name": t.trigger_name,
                "trigger_type": t.trigger_type,
                "threshold_value": t.threshold_value,
                "source_ticker": t.source_ticker,
                "destination_tickers": t.destination_tickers,
                "action_amount_type": t.action_amount_type,
                "action_amount_value": t.action_amount_value,
                "enabled": t.enabled,
                "notes": t.notes,
            }
            for t in crash_plan_triggers
        ],
    }

    import io
    output = io.BytesIO(json.dumps(export_data, default=_serialize_date, indent=2).encode("utf-8"))
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=salubrious-profile.json"},
    )


@router.post("/import")
async def import_profile(file: UploadFile, db: Session = Depends(get_db), user: UserProfile = Depends(get_current_user)):
    """Import complete user profile from JSON. Replaces all existing data for the user."""
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid JSON file")

    if data.get("version") != EXPORT_VERSION:
        raise HTTPException(400, f"Unsupported export version: {data.get('version')}")

    # Delete existing user data (order matters for FK constraints)
    # 1. Delete holdings and contributions (depend on accounts)
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    if account_ids:
        db.query(Holding).filter(Holding.account_id.in_(account_ids)).delete(synchronize_session=False)
        db.query(Contribution).filter(Contribution.account_id.in_(account_ids)).delete(synchronize_session=False)

    # 2. Delete accounts
    db.query(Account).filter(Account.user_id == user.id).delete(synchronize_session=False)

    # 3. Delete policy-related data
    policy = db.query(InvestmentPolicy).filter(InvestmentPolicy.user_id == user.id).first()
    if policy:
        db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).delete(synchronize_session=False)
        db.query(CrashPlanTrigger).filter(CrashPlanTrigger.policy_id == policy.id).delete(synchronize_session=False)
        db.query(ReviewEntry).filter(ReviewEntry.policy_id == policy.id).delete(synchronize_session=False)
        db.query(InvestmentPolicy).filter(InvestmentPolicy.id == policy.id).delete(synchronize_session=False)

    # 4. Delete journal entries and settings
    db.query(JournalEntry).filter(JournalEntry.user_id == user.id).delete(synchronize_session=False)
    db.query(UserSettings).filter(UserSettings.user_id == user.id).delete(synchronize_session=False)

    # Clear identity map so re-used IDs don't conflict
    db.expire_all()

    # Now import fresh data
    summary = {"accounts": 0, "holdings": 0, "contributions": 0, "sleeves": 0, "reviews": 0, "journal_entries": 0, "crash_plan_triggers": 0}

    # Update user profile
    user_data = data.get("user", {})
    if user_data.get("name"):
        user.name = user_data["name"]
    if user_data.get("currency"):
        user.currency = user_data["currency"]

    # Import settings
    settings_data = data.get("settings")
    if settings_data:
        db.add(UserSettings(user_id=user.id, **settings_data))
    else:
        db.add(UserSettings(user_id=user.id))

    # Import policy
    policy_data = data.get("policy")
    if policy_data:
        # Convert date strings back to date objects
        for date_field in ["next_review_date", "last_review_date"]:
            if policy_data.get(date_field) and isinstance(policy_data[date_field], str):
                policy_data[date_field] = date.fromisoformat(policy_data[date_field])
        new_policy = InvestmentPolicy(user_id=user.id, **policy_data)
    else:
        new_policy = InvestmentPolicy(user_id=user.id, name="My Investment Policy")
    db.add(new_policy)
    db.flush()  # Get the policy ID

    # Import sleeves
    for s in data.get("sleeves", []):
        db.add(PortfolioSleeve(policy_id=new_policy.id, **s))
        summary["sleeves"] += 1

    # Import crash plan triggers
    for t in data.get("crash_plan_triggers", []):
        db.add(CrashPlanTrigger(policy_id=new_policy.id, **t))
        summary["crash_plan_triggers"] += 1

    # Import reviews
    for r in data.get("reviews", []):
        if isinstance(r.get("review_date"), str):
            r["review_date"] = date.fromisoformat(r["review_date"])
        db.add(ReviewEntry(policy_id=new_policy.id, **r))
        summary["reviews"] += 1

    # Import accounts with holdings and contributions
    for acct_data in data.get("accounts", []):
        holdings_data = acct_data.pop("holdings", [])
        contributions_data = acct_data.pop("contributions", [])

        new_acct = Account(user_id=user.id, **acct_data)
        db.add(new_acct)
        db.flush()  # Get account ID
        summary["accounts"] += 1

        for h in holdings_data:
            if isinstance(h.get("as_of_date"), str):
                h["as_of_date"] = date.fromisoformat(h["as_of_date"])
            db.add(Holding(account_id=new_acct.id, **h))
            summary["holdings"] += 1

        for c in contributions_data:
            if isinstance(c.get("contribution_date"), str):
                c["contribution_date"] = date.fromisoformat(c["contribution_date"])
            db.add(Contribution(account_id=new_acct.id, **c))
            summary["contributions"] += 1

    # Import journal entries
    for j in data.get("journal_entries", []):
        for date_field in ["entry_date", "follow_up_date"]:
            if j.get(date_field) and isinstance(j[date_field], str):
                j[date_field] = date.fromisoformat(j[date_field])
        db.add(JournalEntry(user_id=user.id, **j))
        summary["journal_entries"] += 1

    db.commit()
    return {"imported": summary}
