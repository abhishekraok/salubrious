from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import InvestmentPolicy, PortfolioSleeve
from ..schemas import (
    InvestmentPolicyOut,
    InvestmentPolicyUpdate,
    PortfolioSleeveCreate,
    PortfolioSleeveOut,
    PortfolioSleeveUpdate,
)

router = APIRouter(prefix="/api/policy", tags=["policy"])


def _get_policy(db: Session) -> InvestmentPolicy:
    policy = db.query(InvestmentPolicy).first()
    if not policy:
        raise HTTPException(404, "No policy found")
    return policy


@router.get("", response_model=InvestmentPolicyOut)
def get_policy(db: Session = Depends(get_db)):
    return _get_policy(db)


@router.put("", response_model=InvestmentPolicyOut)
def update_policy(data: InvestmentPolicyUpdate, db: Session = Depends(get_db)):
    policy = _get_policy(db)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(policy, k, v)
    db.commit()
    db.refresh(policy)
    return policy


# --- Sleeves ---

@router.get("/sleeves", response_model=list[PortfolioSleeveOut])
def get_sleeves(db: Session = Depends(get_db)):
    policy = _get_policy(db)
    return db.query(PortfolioSleeve).filter(PortfolioSleeve.policy_id == policy.id).order_by(PortfolioSleeve.ticker).all()


@router.post("/sleeves", response_model=PortfolioSleeveOut)
def create_sleeve(data: PortfolioSleeveCreate, db: Session = Depends(get_db)):
    policy = _get_policy(db)
    sleeve = PortfolioSleeve(policy_id=policy.id, **data.model_dump())
    db.add(sleeve)
    db.commit()
    db.refresh(sleeve)
    return sleeve


@router.put("/sleeves/{sleeve_id}", response_model=PortfolioSleeveOut)
def update_sleeve(sleeve_id: int, data: PortfolioSleeveUpdate, db: Session = Depends(get_db)):
    sleeve = db.query(PortfolioSleeve).get(sleeve_id)
    if not sleeve:
        raise HTTPException(404, "Sleeve not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sleeve, k, v)
    db.commit()
    db.refresh(sleeve)
    return sleeve


@router.delete("/sleeves/{sleeve_id}")
def delete_sleeve(sleeve_id: int, db: Session = Depends(get_db)):
    sleeve = db.query(PortfolioSleeve).get(sleeve_id)
    if not sleeve:
        raise HTTPException(404, "Sleeve not found")
    db.delete(sleeve)
    db.commit()
    return {"ok": True}
