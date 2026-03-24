"""Price refresh via yfinance with staleness tracking."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Holding, UserProfile

router = APIRouter(prefix="/api/prices", tags=["prices"])

# In-memory tracker — resets on server restart (which is fine: you want fresh prices)
_last_refresh: datetime | None = None
_STALE_SECONDS = 3600  # 1 hour


@router.get("/status")
def price_status():
    """Return whether prices are stale."""
    if _last_refresh is None:
        return {"stale": True, "last_refresh": None}
    age = (datetime.now(timezone.utc) - _last_refresh).total_seconds()
    return {
        "stale": age > _STALE_SECONDS,
        "last_refresh": _last_refresh.isoformat(),
        "age_seconds": int(age),
    }


@router.post("/refresh")
def refresh_prices(db: Session = Depends(get_db)):
    """Fetch latest prices via yfinance and update all holdings."""
    global _last_refresh

    user = db.query(UserProfile).first()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).all()

    if not holdings:
        return {"status": "no_holdings", "updated": 0}

    tickers = list({h.ticker for h in holdings})

    try:
        import yfinance as yf

        # Fetch each ticker individually to avoid MultiIndex issues
        prices: dict[str, float] = {}
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="1d")
                if not hist.empty:
                    prices[ticker] = float(hist["Close"].iloc[-1])
            except Exception:
                continue

        if not prices:
            return {"status": "no_data", "updated": 0}

        updated = 0
        details = []
        for holding in holdings:
            if holding.ticker in prices:
                old_price = holding.price
                old_quantity = holding.quantity
                new_price = prices[holding.ticker]

                # Sanity check: reject clearly wrong prices
                if new_price <= 0:
                    details.append({
                        "ticker": holding.ticker,
                        "skipped": True,
                        "reason": f"invalid price {new_price}",
                    })
                    continue
                if old_price > 0 and (new_price / old_price > 10 or new_price / old_price < 0.1):
                    details.append({
                        "ticker": holding.ticker,
                        "skipped": True,
                        "reason": f"suspicious price change {old_price} -> {new_price}",
                    })
                    continue

                # Only update price and market_value — never quantity
                holding.price = new_price
                holding.market_value = old_quantity * new_price
                holding.as_of_date = date.today()

                assert holding.quantity == old_quantity, (
                    f"BUG: quantity changed for {holding.ticker}: "
                    f"{old_quantity} -> {holding.quantity}"
                )

                details.append({
                    "ticker": holding.ticker,
                    "old_price": round(old_price, 2),
                    "new_price": round(new_price, 2),
                    "quantity": old_quantity,
                    "old_market_value": round(old_quantity * old_price, 2),
                    "new_market_value": round(holding.market_value, 2),
                })
                updated += 1

        db.commit()
        _last_refresh = datetime.now(timezone.utc)
        return {"status": "refreshed", "updated": updated, "details": details}
    except Exception as e:
        return {"status": "error", "message": str(e)}
