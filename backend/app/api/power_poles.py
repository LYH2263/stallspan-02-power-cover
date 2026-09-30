from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import PowerPole, Segment
from app.services.first_fit_engine import validate_power_pole

router = APIRouter(prefix="/power-poles", tags=["power-poles"])

class PowerPoleIn(BaseModel):
    segment_id: int
    position_m: float
    radius_m: float
    label: str = "供电桩"

class PowerPoleUpdate(BaseModel):
    position_m: float
    radius_m: float
    label: str = "供电桩"

def _row(r: PowerPole) -> dict:
    return {"id": r.id, "segment_id": r.segment_id, "position_m": r.position_m,
            "radius_m": r.radius_m, "label": r.label}

def _check(db: Session, segment_id: int, position_m: float, radius_m: float) -> None:
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    err = validate_power_pole(position_m, radius_m, seg.width_m)
    if err:
        raise HTTPException(400, err)

@router.get("")
def list_power_poles(segment_id: int | None = None, db: Session = Depends(get_db)):
    q = select(PowerPole).order_by(PowerPole.segment_id, PowerPole.position_m)
    if segment_id is not None:
        q = q.where(PowerPole.segment_id == segment_id)
    return [_row(r) for r in db.scalars(q).all()]

@router.post("", status_code=201)
def create_power_pole(body: PowerPoleIn, db: Session = Depends(get_db)):
    _check(db, body.segment_id, body.position_m, body.radius_m)
    pole = PowerPole(segment_id=body.segment_id, position_m=body.position_m,
                     radius_m=body.radius_m, label=body.label or "供电桩")
    db.add(pole); db.commit(); db.refresh(pole)
    return _row(pole)

@router.put("/{pole_id}")
def update_power_pole(pole_id: int, body: PowerPoleUpdate, db: Session = Depends(get_db)):
    pole = db.get(PowerPole, pole_id)
    if not pole:
        raise HTTPException(404, "供电桩不存在")
    _check(db, pole.segment_id, body.position_m, body.radius_m)
    pole.position_m = body.position_m
    pole.radius_m = body.radius_m
    pole.label = body.label or "供电桩"
    db.commit(); db.refresh(pole)
    return _row(pole)

@router.delete("/{pole_id}", status_code=204)
def delete_power_pole(pole_id: int, db: Session = Depends(get_db)):
    pole = db.get(PowerPole, pole_id)
    if not pole:
        raise HTTPException(404, "供电桩不存在")
    db.delete(pole); db.commit()
