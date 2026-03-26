"""Account and holding management, including CSV import."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..fund_metadata import lookup_fund
from ..models import Account, Holding, InvestmentPolicy, PortfolioSleeve, UserProfile
from ..schemas import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    HoldingCreate,
    HoldingOut,
    HoldingUpdate,
)

router = APIRouter(prefix="/api", tags=["portfolio"])


# --- Accounts ---

@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    return db.query(Account).filter(Account.user_id == user.id).all()


@router.post("/accounts", response_model=AccountOut)
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    account = Account(user_id=user.id, **data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    db.query(Holding).filter(Holding.account_id == account_id).delete()
    db.delete(account)
    db.commit()
    return {"ok": True}


# --- Holdings ---

@router.get("/accounts/{account_id}/holdings", response_model=list[HoldingOut])
def list_holdings(account_id: int, db: Session = Depends(get_db)):
    return db.query(Holding).filter(Holding.account_id == account_id).order_by(Holding.ticker).all()


@router.get("/holdings", response_model=list[HoldingOut])
def list_all_holdings(db: Session = Depends(get_db)):
    user = db.query(UserProfile).first()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_ids = [a.id for a in accounts]
    return db.query(Holding).filter(Holding.account_id.in_(account_ids)).order_by(Holding.ticker).all()


@router.post("/accounts/{account_id}/holdings", response_model=HoldingOut)
def create_holding(account_id: int, data: HoldingCreate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    holding = Holding(
        account_id=account_id,
        ticker=data.ticker.upper(),
        quantity=data.quantity,
        price=data.price,
        market_value=data.quantity * data.price,
        as_of_date=data.as_of_date or date.today(),
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.put("/holdings/{holding_id}", response_model=HoldingOut)
def update_holding(holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    holding = db.query(Holding).get(holding_id)
    if not holding:
        raise HTTPException(404, "Holding not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(holding, k, v)
    if data.quantity is not None or data.price is not None:
        holding.market_value = holding.quantity * holding.price
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(Holding).get(holding_id)
    if not holding:
        raise HTTPException(404, "Holding not found")
    db.delete(holding)
    db.commit()
    return {"ok": True}


# --- CSV Export ---

@router.get("/holdings/export")
def export_holdings_csv(db: Session = Depends(get_db)):
    """Export all holdings as a CSV file."""
    user = db.query(UserProfile).first()
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_map = {a.id: a for a in accounts}
    account_ids = [a.id for a in accounts]
    holdings = db.query(Holding).filter(Holding.account_id.in_(account_ids)).order_by(Holding.ticker).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["account", "ticker", "quantity", "price", "market_value", "as_of_date"])
    for h in holdings:
        acct = account_map[h.account_id]
        writer.writerow([acct.account_name, h.ticker, h.quantity, round(h.price, 2), round(h.market_value, 2), h.as_of_date])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=holdings.csv"},
    )


@router.get("/accounts/{account_id}/holdings/export")
def export_account_holdings_csv(account_id: int, db: Session = Depends(get_db)):
    """Export holdings for a single account as a CSV file."""
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    holdings = db.query(Holding).filter(Holding.account_id == account_id).order_by(Holding.ticker).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ticker", "quantity", "price", "market_value", "as_of_date"])
    for h in holdings:
        writer.writerow([h.ticker, h.quantity, round(h.price, 2), round(h.market_value, 2), h.as_of_date])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={account.account_name}_holdings.csv"},
    )


# --- CSV Import ---

@router.post("/accounts/{account_id}/holdings/csv")
async def import_csv(account_id: int, file: UploadFile, db: Session = Depends(get_db)):
    """Import holdings from CSV. Expected columns: ticker, quantity, price (or market_value)."""
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    # Clear existing holdings for this account
    db.query(Holding).filter(Holding.account_id == account_id).delete()

    imported = 0
    for row in reader:
        ticker = row.get("ticker", "").strip().upper()
        if not ticker:
            continue

        quantity = float(row.get("quantity", 0))
        price = float(row.get("price", 0))
        market_value = float(row.get("market_value", 0))

        if price == 0 and market_value > 0 and quantity > 0:
            price = market_value / quantity
        if market_value == 0 and price > 0:
            market_value = quantity * price

        db.add(Holding(
            account_id=account_id,
            ticker=ticker,
            quantity=quantity,
            price=price,
            market_value=market_value,
            as_of_date=date.today(),
        ))
        imported += 1

    # Auto-create sleeve stubs for tickers not already in the fund list
    policy = db.query(InvestmentPolicy).filter(
        InvestmentPolicy.user_id == account.user_id
    ).first()
    if policy:
        existing_tickers = {
            s.ticker for s in
            db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).all()
        }
        new_holdings = db.query(Holding).filter(
            Holding.account_id == account_id,
            ~Holding.ticker.in_(existing_tickers) if existing_tickers else True,
        ).all()
        for h in new_holdings:
            if h.ticker not in existing_tickers:
                meta = lookup_fund(h.ticker)
                if meta:
                    db.add(PortfolioSleeve(
                        policy_id=policy.id,
                        ticker=h.ticker,
                        target_percent=0,
                        **meta,
                    ))
                else:
                    db.add(PortfolioSleeve(
                        policy_id=policy.id,
                        ticker=h.ticker,
                        label=h.ticker,
                        target_percent=0,
                        asset_class="equity",
                        is_safe_asset=False,
                        is_cash_like=False,
                    ))
                existing_tickers.add(h.ticker)

    db.commit()
    return {"imported": imported}
