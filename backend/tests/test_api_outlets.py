"""API-level checks for power outlets CRUD validation and the single shared
coverage decision used by both the map (placements) and 放不下 (rejected).

Runs against SQLite via a get_db override so it needs no Postgres.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import MarketDay, Pillar, PowerOutlet, Segment, Vendor


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = TestSession()
    day = MarketDay(name="测试日", day="2026-09-30")
    db.add(day); db.flush()
    seg = Segment(market_day_id=day.id, name="东街段", width_m=30.0)
    db.add(seg); db.flush()
    db.add(Pillar(segment_id=seg.id, position_m=10.0, thickness_m=0.5, label="灯柱A"))
    db.add(Pillar(segment_id=seg.id, position_m=20.0, thickness_m=0.5, label="灯柱B"))
    for i, (name, w, pri) in enumerate([
        ("短摊甲", 3.0, 1), ("短摊乙", 2.0, 1), ("宽摊一", 5.0, 2),
        ("宽摊二", 5.0, 2), ("宽摊三", 5.0, 3), ("巨型舞台车", 12.0, 9),
    ]):
        db.add(Vendor(market_day_id=day.id, name=name, stall_width_m=w, priority=pri))
    db.commit()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestSession
    app.dependency_overrides.clear()
    db.close()


def _outlet_count(Session):
    with Session() as s:
        return s.scalar(select(func.count()).select_from(PowerOutlet))


def test_invalid_writes_are_rejected_and_leave_no_dirty_rows(client):
    c, Session = client
    base = {"segment_id": 1, "position_m": 5.0, "radius_m": 5.0, "label": "供电桩A"}
    for bad in [
        {**base, "radius_m": 0.0},
        {**base, "radius_m": -1.0},
        {**base, "position_m": 31.0},
        {**base, "position_m": -0.1},
    ]:
        r = c.post("/api/outlets", json=bad)
        assert r.status_code == 400, bad
    assert _outlet_count(Session) == 0


def test_valid_outlet_persists_across_reads(client):
    c, Session = client
    r = c.post("/api/outlets", json={"segment_id": 1, "position_m": 5.0, "radius_m": 5.0})
    assert r.status_code == 201
    oid = r.json()["id"]
    assert c.get("/api/outlets").json()[0]["id"] == oid
    r2 = c.put(f"/api/outlets/{oid}", json={"segment_id": 1, "position_m": 6.0, "radius_m": 4.0})
    assert r2.status_code == 200
    again = c.get("/api/outlets").json()[0]
    assert again["position_m"] == 6.0 and again["radius_m"] == 4.0
    assert c.delete(f"/api/outlets/{oid}").status_code == 204
    assert c.get("/api/outlets").json() == []


def test_green_field_when_no_outlets(client):
    c, _ = client
    data = c.post("/api/allocate/run?segment_id=1").json()
    assert data["outlets"] == []
    names = {p["vendor_name"] for p in data["placements"]}
    # geometry alone decides; the 12m truck can never fit a <10m pillar bay
    assert "巨型舞台车" not in names
    assert all(not x["reason"].startswith("供电不足") for x in data["rejected"])


def test_coverage_is_shared_between_map_and_rejected(client):
    c, _ = client
    # outlets cover bays 1 and 2 only; bay 3 (20.25..30) is dark
    for pos in (5.0, 15.0):
        assert c.post("/api/outlets", json={
            "segment_id": 1, "position_m": pos, "radius_m": 5.0}).status_code == 201
    data = c.post("/api/allocate/run?segment_id=1").json()
    # every stall drawn on the map is fully inside one outlet's closed interval
    for p in data["placements"]:
        assert any(p["start_m"] >= o["position_m"] - o["radius_m"] - 1e-9
                   and p["end_m"] <= o["position_m"] + o["radius_m"] + 1e-9
                   for o in data["outlets"])
    # legal placements and rejected names partition the full vendor set
    placed = {p["vendor_name"] for p in data["placements"]}
    rejected = {x["vendor_name"]: x["reason"] for x in data["rejected"]}
    assert placed.isdisjoint(rejected)
    assert placed | set(rejected) == {
        "短摊甲", "短摊乙", "宽摊一", "宽摊二", "宽摊三", "巨型舞台车"}
    # a stall whose only remaining room is the dark bay shows 供电不足
    assert any(reason.startswith("供电不足") for reason in rejected.values())
    assert rejected["巨型舞台车"].startswith("供电不足") is False
    # mutually exclusive reasons: power failures are their own sentence
    for reason in rejected.values():
        assert not (reason.startswith("供电不足") and "空档" in reason)


def test_latest_recomputes_after_outlet_change_instead_of_stale_coverage(client):
    c, _ = client
    oid = c.post("/api/outlets", json={"segment_id": 1, "position_m": 5.0, "radius_m": 5.0}).json()["id"]
    first = c.post("/api/allocate/run?segment_id=1").json()
    run_id = first["id"]
    assert first["outlets"] == [{"position_m": 5.0, "radius_m": 5.0, "label": "供电桩"}]
    # move the post; /latest must not serve the pre-change coverage
    c.put(f"/api/outlets/{oid}", json={"segment_id": 1, "position_m": 25.0, "radius_m": 5.0})
    latest = c.get("/api/allocate/latest?segment_id=1").json()
    assert latest["id"] != run_id
    assert latest["outlets"] == [{"position_m": 25.0, "radius_m": 5.0, "label": "供电桩"}]
    assert all(p["start_m"] >= 20.0 - 1e-9 for p in latest["placements"])
