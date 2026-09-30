from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import MarketDay, Pillar, PowerPole, Segment, Vendor

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(MarketDay)) or 0) > 0:
        return
    day = MarketDay(name="周末夜市", day=date(2026, 9, 20))
    db.add(day); db.flush()
    seg = Segment(market_day_id=day.id, name="东街段", width_m=40.0)
    db.add(seg); db.flush()
    db.add(Pillar(segment_id=seg.id, position_m=10.0, thickness_m=0.5, label="灯柱A"))
    db.add(Pillar(segment_id=seg.id, position_m=20.0, thickness_m=0.5, label="灯柱B"))
    # 供电桩：单桩服务窗 10m。巨型舞台车 12m 无任何单桩能完全盖住 → 供电不足进放不下；
    # 宽度更短且落在桩边的摊仍可正常落位。
    db.add(PowerPole(segment_id=seg.id, position_m=5.0, radius_m=5.0, label="电桩A"))
    db.add(PowerPole(segment_id=seg.id, position_m=15.0, radius_m=5.0, label="电桩B"))
    db.add(PowerPole(segment_id=seg.id, position_m=25.0, radius_m=5.0, label="电桩C"))
    vendors = [
        ("阿强烧烤", 4.0, 1), ("林记糖水", 3.0, 1), ("老周水果", 5.0, 2),
        ("小美饰品", 2.5, 2), ("大碗面", 6.0, 1), ("手作皮具", 3.5, 3),
        ("巨型舞台车", 12.0, 9),
    ]
    for name, wdt, pri in vendors:
        db.add(Vendor(market_day_id=day.id, name=name, stall_width_m=wdt, priority=pri))
    db.commit()
