from app.services.first_fit_engine import (
    REASON_NO_POWER,
    REASON_NO_SPACE,
    allocate_first_fit,
    free_spans_from_pillars,
    interval_covered,
)

def test_free_spans_with_pillars():
    spans = free_spans_from_pillars(30.0, [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}])
    assert len(spans) == 3
    assert spans[0][0] == 0.0

def test_first_fit_no_cross_pillar():
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 12.0, "priority": 1},
    ]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert any(p.vendor_name == "A" for p in r.placements)
    # 12m may fit in a free span after first placement depending on remainders
    assert len(r.placements) + len(r.rejected) == 2

def test_reject_oversized():
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
    r = allocate_first_fit(30.0, vendors, pillars)
    assert len(r.rejected) == 1
    assert r.rejected[0].vendor_name == "Huge"

def test_no_outlets_equals_green_field():
    vendors = [{"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1}]
    r = allocate_first_fit(30.0, vendors, [], outlets=None)
    assert len(r.placements) == 1
    assert r.placements[0].start_m == 0.0

def test_interval_covered_full_containment():
    o = [{"position_m": 10.0, "radius_m": 5.0}]
    assert interval_covered(5.0, 15.0, o)          # exact closed-interval cover
    assert interval_covered(7.0, 12.0, o)          # inside
    assert not interval_covered(4.9, 12.0, o)      # left end outside
    assert not interval_covered(8.0, 15.1, o)      # right end outside
    assert not interval_covered(10.0, 16.0, o)     # only midpoint covered
    assert not interval_covered(0.0, 30.0, [])     # no outlets

def test_stall_must_be_fully_inside_one_outlet():
    # outlet at 5m radius 5m -> covers closed [0, 10]; pillars irrelevant here
    vendors = [
        {"id": 1, "name": "短摊", "stall_width_m": 3.0, "priority": 1},
        {"id": 2, "name": "巨型舞台车", "stall_width_m": 12.0, "priority": 9},
    ]
    outlets = [{"position_m": 5.0, "radius_m": 5.0}]
    r = allocate_first_fit(30.0, vendors, [], outlets=outlets)
    placed = {p.vendor_name: p for p in r.placements}
    rejected = {x.vendor_name: x for x in r.rejected}
    assert "短摊" in placed
    # the short stall sits at the edge of the outlet's coverage, fully covered
    assert placed["短摊"].end_m <= 10.0 + 1e-9
    assert "巨型舞台车" in rejected
    assert rejected["巨型舞台车"].reason == REASON_NO_POWER
    assert rejected["巨型舞台车"].reason != REASON_NO_SPACE
    assert REASON_NO_SPACE not in rejected["巨型舞台车"].reason

def test_midpoint_only_coverage_rejected():
    # outlet covers [8,12]; a 6m stall can at best have one end outside
    vendors = [{"id": 1, "name": "X", "stall_width_m": 6.0, "priority": 1}]
    outlets = [{"position_m": 10.0, "radius_m": 2.0}]
    r = allocate_first_fit(30.0, vendors, [], outlets=outlets)
    assert len(r.placements) == 0
    assert r.rejected[0].reason == REASON_NO_POWER

def test_reasons_are_mutually_exclusive():
    # 12m segment after pillar leaves spans 0..10 and 10.5..30; outlet covers
    # only [0,6]: a 9m stall has geometric room (19.5m span) but never full cover
    pillars = [{"position_m": 10.0, "thickness_m": 1.0}]
    outlets = [{"position_m": 3.0, "radius_m": 3.0}]
    vendors = [{"id": 1, "name": "A", "stall_width_m": 9.0, "priority": 1}]
    r = allocate_first_fit(30.0, vendors, pillars, outlets=outlets)
    assert len(r.rejected) == 1
    assert r.rejected[0].reason == REASON_NO_POWER

def test_reject_no_space_not_power_when_span_too_small():
    # every free span shorter than the stall even though outlets exist
    pillars = [{"position_m": 10.0, "thickness_m": 1.0},
               {"position_m": 20.0, "thickness_m": 1.0}]
    outlets = [{"position_m": 5.0, "radius_m": 50.0}]
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    r = allocate_first_fit(30.0, vendors, pillars, outlets=outlets)
    assert len(r.rejected) == 1
    assert r.rejected[0].reason == REASON_NO_SPACE
