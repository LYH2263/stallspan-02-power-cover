from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import AllocationRun, MarketDay, Pillar, PowerOutlet, Segment, Vendor

# East segment: pillars at 10m/20m split 30m into three bays.
# Outlets cover only the first two bays ([0,10] and [10,20]); the third bay
# has no power. Short stalls pack at the coverage edges and still land, a stall
# whose only free room is the dark bay is rejected as 供电不足, and the 12m
# 巨型舞台车 cannot be fully covered by any single 10m-diameter post so it
# lands in 放不下.
_SEED_OUTLETS = [(5.0, 5.0, "供电桩A"), (15.0, 5.0, "供电桩B")]


def _add_outlets(db: Session, segment_id: int) -> None:
    for pos, radius, label in _SEED_OUTLETS:
        db.add(PowerOutlet(segment_id=segment_id, position_m=pos, radius_m=radius, label=label))


def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(MarketDay)) or 0) > 0:
        _backfill_seed_outlets(db)
        return
    day = MarketDay(name="周末夜市", day=date(2026, 9, 20))
    db.add(day); db.flush()
    seg = Segment(market_day_id=day.id, name="东街段", width_m=30.0)
    db.add(seg); db.flush()
    db.add(Pillar(segment_id=seg.id, position_m=10.0, thickness_m=0.5, label="灯柱A"))
    db.add(Pillar(segment_id=seg.id, position_m=20.0, thickness_m=0.5, label="灯柱B"))
    _add_outlets(db, seg.id)
    vendors = [
        ("阿强烧烤", 4.0, 1), ("林记糖水", 3.0, 1), ("老周水果", 5.0, 2),
        ("小美饰品", 2.5, 2), ("大碗面", 6.0, 1), ("手作皮具", 3.5, 3),
        ("巨型舞台车", 12.0, 9),
    ]
    for name, wdt, pri in vendors:
        db.add(Vendor(market_day_id=day.id, name=name, stall_width_m=wdt, priority=pri))
    db.commit()


def _backfill_seed_outlets(db: Session) -> None:
    """One-time backfill for databases seeded before power outlets existed.

    Only runs on a database that has never held an outlet and never run an
    allocation; afterwards user edits/deletes are the source of truth and are
    never re-seeded.
    """
    if (db.scalar(select(func.count()).select_from(PowerOutlet)) or 0) > 0:
        return
    if (db.scalar(select(func.count()).select_from(AllocationRun)) or 0) > 0:
        return
    segs = db.scalars(select(Segment).where(Segment.name == "东街段")).all()
    if not segs:
        return
    for seg in segs:
        _add_outlets(db, seg.id)
    db.commit()
