import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import AllocationRun, Pillar, PowerOutlet, Segment, Vendor
from app.services.first_fit_engine import allocate_first_fit, result_to_dict
router = APIRouter(prefix="/allocate", tags=["allocate"])

def _compute(segment_id: int, db: Session) -> dict:
    """Always recompute from the current pillars AND power outlets so a changed
    outlet can never be drawn from a stale coverage result."""
    seg = db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "街段不存在")
    pillars = [{"position_m": p.position_m, "thickness_m": p.thickness_m}
               for p in db.scalars(select(Pillar).where(Pillar.segment_id == segment_id)).all()]
    outlets = [{"position_m": o.position_m, "radius_m": o.radius_m, "label": o.label}
               for o in db.scalars(select(PowerOutlet).where(PowerOutlet.segment_id == segment_id)).all()]
    vendors = [{"id": v.id, "name": v.name, "stall_width_m": v.stall_width_m, "priority": v.priority}
               for v in db.scalars(select(Vendor).where(Vendor.market_day_id == seg.market_day_id)).all()]
    result = result_to_dict(allocate_first_fit(seg.width_m, vendors, pillars, outlets))
    result["segment"] = {"id": seg.id, "name": seg.name, "width_m": seg.width_m}
    result["pillars"] = pillars
    result["outlets"] = outlets
    return result

@router.post("/run")
def run_allocate(segment_id: int = 1, db: Session = Depends(get_db)):
    result = _compute(segment_id, db)
    run = AllocationRun(segment_id=segment_id, created_at=datetime.utcnow(),
                        result_json=json.dumps(result, ensure_ascii=False))
    db.add(run); db.commit(); db.refresh(run)
    return {"id": run.id, **result}

@router.get("/latest")
def latest(segment_id: int = 1, db: Session = Depends(get_db)):
    run = db.scalars(select(AllocationRun).where(AllocationRun.segment_id == segment_id)
                     .order_by(AllocationRun.id.desc())).first()
    if not run:
        return run_allocate(segment_id=segment_id, db=db)
    data = json.loads(run.result_json)
    # Stored coverage must match the current pillars/outlets; if a post was
    # moved/added/removed after this run, recompute instead of serving stale
    # coverage (map and 放不下 share exactly this computation).
    seg = db.get(Segment, segment_id)
    if seg is None:
        raise HTTPException(404, "街段不存在")
    cur_pillars = [{"position_m": p.position_m, "thickness_m": p.thickness_m}
                   for p in db.scalars(select(Pillar).where(Pillar.segment_id == segment_id)).all()]
    cur_outlets = [{"position_m": o.position_m, "radius_m": o.radius_m}
                   for o in db.scalars(select(PowerOutlet).where(PowerOutlet.segment_id == segment_id)).all()]
    if data.get("pillars") != cur_pillars or data.get("outlets") != cur_outlets:
        return run_allocate(segment_id=segment_id, db=db)
    return {"id": run.id, **data}
