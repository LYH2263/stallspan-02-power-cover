import math

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import PowerOutlet, Segment

router = APIRouter(prefix="/outlets", tags=["outlets"])


class OutletIn(BaseModel):
    segment_id: int
    position_m: float
    radius_m: float
    label: str | None = "供电桩"


def _validate(seg: Segment, position_m: float, radius_m: float) -> None:
    """Reject radius<=0 or out-of-range/non-finite writes so no dirty row lands."""
    if not (math.isfinite(position_m) and math.isfinite(radius_m)):
        raise HTTPException(400, "位置与半径必须为有限数值")
    if radius_m <= 0:
        raise HTTPException(400, "供电桩服务半径必须大于 0")
    if position_m < 0.0 or position_m > seg.width_m:
        raise HTTPException(400, f"位置越界：必须在 0 与街段宽度 {seg.width_m} 之间")


@router.get("")
def list_outlets(segment_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(PowerOutlet).order_by(PowerOutlet.segment_id, PowerOutlet.position_m)
    if segment_id is not None:
        stmt = stmt.where(PowerOutlet.segment_id == segment_id)
    return [{"id": r.id, "segment_id": r.segment_id, "position_m": r.position_m,
             "radius_m": r.radius_m, "label": r.label}
            for r in db.scalars(stmt).all()]


@router.post("", status_code=201)
def create_outlet(body: OutletIn, db: Session = Depends(get_db)):
    seg = db.get(Segment, body.segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    _validate(seg, body.position_m, body.radius_m)
    row = PowerOutlet(segment_id=seg.id, position_m=body.position_m,
                      radius_m=body.radius_m, label=(body.label or "供电桩")[:32])
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "segment_id": row.segment_id, "position_m": row.position_m,
            "radius_m": row.radius_m, "label": row.label}


@router.put("/{outlet_id}")
def update_outlet(outlet_id: int, body: OutletIn, db: Session = Depends(get_db)):
    row = db.get(PowerOutlet, outlet_id)
    if not row:
        raise HTTPException(404, "供电桩不存在")
    seg = db.get(Segment, body.segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    _validate(seg, body.position_m, body.radius_m)
    row.segment_id = seg.id
    row.position_m = body.position_m
    row.radius_m = body.radius_m
    row.label = (body.label or "供电桩")[:32]
    db.commit()
    db.refresh(row)
    return {"id": row.id, "segment_id": row.segment_id, "position_m": row.position_m,
            "radius_m": row.radius_m, "label": row.label}


@router.delete("/{outlet_id}", status_code=204)
def delete_outlet(outlet_id: int, db: Session = Depends(get_db)):
    row = db.get(PowerOutlet, outlet_id)
    if not row:
        raise HTTPException(404, "供电桩不存在")
    db.delete(row)
    db.commit()
