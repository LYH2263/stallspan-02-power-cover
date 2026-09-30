from app.services.first_fit_engine import (
    allocate_first_fit, covered_start, free_spans_from_pillars,
    interval_covered, validate_power_pole,
)

SEED_PILLARS = [{"position_m": 10.0, "thickness_m": 0.5}, {"position_m": 20.0, "thickness_m": 0.5}]
SEED_POLES = [
    {"position_m": 5.0, "radius_m": 5.0},
    {"position_m": 15.0, "radius_m": 5.0},
    {"position_m": 25.0, "radius_m": 5.0},
]
SEED_VENDORS = [
    {"id": 1, "name": "阿强烧烤", "stall_width_m": 4.0, "priority": 1},
    {"id": 2, "name": "林记糖水", "stall_width_m": 3.0, "priority": 1},
    {"id": 3, "name": "老周水果", "stall_width_m": 5.0, "priority": 2},
    {"id": 4, "name": "小美饰品", "stall_width_m": 2.5, "priority": 2},
    {"id": 5, "name": "大碗面", "stall_width_m": 6.0, "priority": 1},
    {"id": 6, "name": "手作皮具", "stall_width_m": 3.5, "priority": 3},
    {"id": 7, "name": "巨型舞台车", "stall_width_m": 12.0, "priority": 9},
]

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

# ---- power pole coverage ----

def test_no_poles_same_as_before():
    """未配置任何供电桩时行为与绿仓相同：不加任何覆盖限制。"""
    vendors = [dict(v) for v in SEED_VENDORS]
    r_none = allocate_first_fit(40.0, vendors, SEED_PILLARS, None)
    r_empty = allocate_first_fit(40.0, [dict(v) for v in SEED_VENDORS], SEED_PILLARS, [])
    assert [(p.vendor_id, p.start_m, p.end_m) for p in r_none.placements] == \
           [(p.vendor_id, p.start_m, p.end_m) for p in r_empty.placements]
    # 无桩时 12m 舞台车只看空档：40m 街段空档够，应落位而非供电不足
    assert any(p.vendor_name == "巨型舞台车" for p in r_none.placements)
    assert all("供电" not in x.reason for x in r_none.rejected)

def test_fully_covered_stall_placed():
    vendors = [{"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1}]
    poles = [{"position_m": 5.0, "radius_m": 5.0}]  # 服务窗 [0,10]
    r = allocate_first_fit(20.0, vendors, [], poles)
    assert len(r.placements) == 1
    p = r.placements[0]
    assert interval_covered(p.start_m, p.end_m, poles)

def test_shifted_into_coverage():
    """自然落点露出半径外时，应右移到被完全盖住的最近位置。"""
    vendors = [{"id": 1, "name": "A", "stall_width_m": 3.0, "priority": 1}]
    poles = [{"position_m": 8.0, "radius_m": 4.0}]  # 服务窗 [4,12]
    r = allocate_first_fit(20.0, vendors, [], poles)
    assert len(r.placements) == 1
    assert r.placements[0].start_m == 4.0  # 从 0 右移到窗沿
    assert r.placements[0].end_m == 7.0

def test_midpoint_covered_but_ends_out_rejected():
    """只盖住中点、两端露在半径外 → 供电不足。"""
    vendors = [{"id": 1, "name": "A", "stall_width_m": 8.0, "priority": 1}]
    poles = [{"position_m": 10.0, "radius_m": 3.0}]  # 服务窗 [7,13]，盖不住 8m
    r = allocate_first_fit(20.0, vendors, [], poles)
    assert len(r.placements) == 0
    assert len(r.rejected) == 1
    assert "供电不足" in r.rejected[0].reason

def test_one_end_out_rejected():
    """落位后一端露在半径外 → 供电不足，且拒因不与空档不够合并。"""
    vendors = [
        {"id": 1, "name": "A", "stall_width_m": 4.0, "priority": 1},
        {"id": 2, "name": "B", "stall_width_m": 5.0, "priority": 2},
    ]
    pillars = [{"position_m": 10.0, "thickness_m": 0.5}]
    poles = [{"position_m": 13.0, "radius_m": 3.0}]  # 服务窗 [10,16]
    r = allocate_first_fit(20.0, vendors, pillars, poles)
    assert [p.vendor_name for p in r.placements] == ["A"]
    assert len(r.rejected) == 1
    rej = r.rejected[0]
    assert rej.vendor_name == "B"
    assert "供电不足" in rej.reason
    assert "空档" not in rej.reason  # 拒因互斥：不与空档不够并成一句

def test_union_of_two_poles_not_enough():
    """两桩服务窗并起来够长也不算：必须单桩完全盖住。"""
    vendors = [{"id": 1, "name": "A", "stall_width_m": 12.0, "priority": 1}]
    poles = [{"position_m": 5.0, "radius_m": 5.0}, {"position_m": 15.0, "radius_m": 5.0}]
    r = allocate_first_fit(30.0, vendors, [], poles)
    assert len(r.placements) == 0
    assert "供电不足" in r.rejected[0].reason

def test_space_reason_when_no_room_even_with_poles():
    """空档真的不够时仍报空档原因，不得写成供电不足。"""
    vendors = [{"id": 1, "name": "Huge", "stall_width_m": 25.0, "priority": 1}]
    r = allocate_first_fit(30.0, vendors, SEED_PILLARS, SEED_POLES)
    assert len(r.rejected) == 1
    assert "空档" in r.rejected[0].reason
    assert "供电不足" not in r.rejected[0].reason

def test_reasons_mutually_exclusive():
    vendors = [
        {"id": 1, "name": "TooBig", "stall_width_m": 45.0, "priority": 1},
        {"id": 2, "name": "NoPower", "stall_width_m": 8.0, "priority": 2},
    ]
    poles = [{"position_m": 10.0, "radius_m": 3.0}]
    r = allocate_first_fit(40.0, vendors, [], poles)
    assert len(r.rejected) == 2
    by_name = {x.vendor_name: x.reason for x in r.rejected}
    assert "供电不足" not in by_name["TooBig"]
    assert "供电不足" in by_name["NoPower"] and "空档" not in by_name["NoPower"]

def test_covered_start_helper():
    poles = [{"position_m": 25.0, "radius_m": 5.0}]  # [20,30]
    assert covered_start(20.25, 40.0, 5.0, poles) == 20.25
    assert covered_start(25.25, 40.0, 12.0, poles) is None  # 12m 单桩盖不住
    assert covered_start(0.0, 9.75, 4.0, poles) is None     # 窗口不在该空档内

def test_interval_covered_closed_interval():
    poles = [{"position_m": 5.0, "radius_m": 5.0}]  # [0,10]
    assert interval_covered(0.0, 10.0, poles)       # 闭区间端点贴着也算盖住
    assert interval_covered(2.0, 8.0, poles)
    assert not interval_covered(0.0, 10.5, poles)   # 一端外露
    assert not interval_covered(-0.5, 5.0, poles)
    assert not interval_covered(2.0, 8.0, [])       # 无桩

def test_seed_scenario_stage_truck_rejected_power():
    """种子场景：东街段 40m + 三桩 r5 → 舞台车供电不足，短摊落桩边仍可落。"""
    r = allocate_first_fit(40.0, [dict(v) for v in SEED_VENDORS], SEED_PILLARS, SEED_POLES)
    placed = {p.vendor_name: p for p in r.placements}
    assert len(placed) == 6
    assert "巨型舞台车" not in placed
    assert len(r.rejected) == 1
    rej = r.rejected[0]
    assert rej.vendor_name == "巨型舞台车"
    assert "供电不足" in rej.reason and "空档" not in rej.reason
    # 图上只出现覆盖合法的摊：每个落位都必须被单桩完全盖住
    for p in r.placements:
        assert interval_covered(p.start_m, p.end_m, SEED_POLES), p.vendor_name

def test_validate_power_pole():
    assert validate_power_pole(5.0, 0.0, 40.0) is not None    # 半径 ≤ 0 拒绝
    assert validate_power_pole(5.0, -1.0, 40.0) is not None
    assert validate_power_pole(-0.1, 3.0, 40.0) is not None   # 位置越界拒绝
    assert validate_power_pole(40.1, 3.0, 40.0) is not None
    assert validate_power_pole(0.0, 3.0, 40.0) is None        # 边界合法
    assert validate_power_pole(40.0, 3.0, 40.0) is None
    assert validate_power_pole(20.0, 5.0, 40.0) is None
