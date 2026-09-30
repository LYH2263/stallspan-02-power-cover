"""1D First-Fit stall placement along a street segment; stalls cannot cross pillars.

Power-pole coverage: when a segment has power poles registered, a placed stall's
closed [start_m, end_m] interval must be fully contained in at least ONE pole's
service interval [position_m - radius_m, position_m + radius_m]. Covering only
the midpoint, or leaving either end outside the radius, is rejected. The union
of several poles does NOT count — a single pole must cover the whole stall.
With no poles configured the power constraint is disabled entirely (same
behaviour as before poles existed).
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

EPS = 1e-9

REASON_NO_SPACE = "无连续空档可放下且不跨越挡柱"
REASON_NO_POWER = "供电不足：起止区间未被任一供电桩服务半径完全覆盖"

@dataclass
class Placement:
    vendor_id: int
    vendor_name: str
    start_m: float
    end_m: float
    width_m: float

@dataclass
class Rejected:
    vendor_id: int
    vendor_name: str
    width_m: float
    reason: str

@dataclass
class AllocResult:
    placements: list[Placement]
    rejected: list[Rejected]
    free_spans: list[tuple[float, float]]

def free_spans_from_pillars(width_m: float, pillars: list[dict]) -> list[tuple[float, float]]:
    """pillars: position_m, thickness_m — treated as blocked intervals."""
    blocked = []
    for p in pillars:
        half = p.get("thickness_m", 0.4) / 2.0
        lo = max(0.0, p["position_m"] - half)
        hi = min(width_m, p["position_m"] + half)
        if hi > lo:
            blocked.append((lo, hi))
    blocked.sort()
    merged = []
    for lo, hi in blocked:
        if not merged or lo > merged[-1][1]:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    spans = []
    cursor = 0.0
    for lo, hi in merged:
        if lo > cursor:
            spans.append((cursor, lo))
        cursor = hi
    if cursor < width_m:
        spans.append((cursor, width_m))
    return [(round(a, 3), round(b, 3)) for a, b in spans if b - a > 1e-6]

def interval_covered(start_m: float, end_m: float, power_poles: list[dict]) -> bool:
    """True iff [start_m, end_m] is fully contained in one single pole's service interval."""
    for p in power_poles:
        r = p.get("radius_m", 0.0)
        if r <= 0:
            continue
        lo = p["position_m"] - r
        hi = p["position_m"] + r
        if lo - EPS <= start_m and end_m <= hi + EPS:
            return True
    return False

def covered_start(span_lo: float, span_hi: float, need: float, power_poles: list[dict]) -> float | None:
    """Leftmost x such that [x, x+need] fits inside [span_lo, span_hi] AND is fully
    covered by one single pole's service interval. None if no such position exists."""
    best = None
    for p in power_poles:
        r = p.get("radius_m", 0.0)
        if r <= 0:
            continue
        lo = max(span_lo, p["position_m"] - r)
        hi = min(span_hi - need, p["position_m"] + r - need)
        if lo <= hi + EPS and (best is None or lo < best):
            best = lo
    return best

def validate_power_pole(position_m: float, radius_m: float, width_m: float) -> str | None:
    """Return an error message when the pole write is illegal, else None.
    radius must be > 0 and position must lie inside the segment [0, width_m]."""
    if radius_m <= 0:
        return "服务半径必须大于 0"
    if position_m < 0 or position_m > width_m:
        return f"位置越界：须在街段范围 0~{width_m} m 内"
    return None

def allocate_first_fit(width_m: float, vendors: list[dict], pillars: list[dict],
                       power_poles: list[dict] | None = None) -> AllocResult:
    """vendors sorted by priority ascending then id; each needs stall_width_m contiguous
    in one free span (no pillar cross) and, when power poles exist, fully covered by one pole."""
    spans = free_spans_from_pillars(width_m, pillars)
    # mutable remaining capacity per span
    remain = [[a, b] for a, b in spans]
    poles = [p for p in (power_poles or []) if p.get("radius_m", 0.0) > 0]
    ordered = sorted(vendors, key=lambda v: (v.get("priority", 1), v["id"]))
    placements: list[Placement] = []
    rejected: list[Rejected] = []
    for v in ordered:
        need = float(v["stall_width_m"])
        placed = False
        space_possible = False
        for span in remain:
            avail = span[1] - span[0]
            if avail + EPS < need:
                continue
            space_possible = True
            if poles:
                start = covered_start(span[0], span[1], need, poles)
                if start is None:
                    continue
            else:
                start = span[0]
            end = start + need
            placements.append(Placement(v["id"], v["name"], round(start, 3), round(end, 3), need))
            span[0] = end
            placed = True
            break
        if not placed:
            # mutually exclusive reasons: power only when space alone would have fit
            reason = REASON_NO_POWER if (poles and space_possible) else REASON_NO_SPACE
            rejected.append(Rejected(v["id"], v["name"], need, reason))
    free = [(round(a, 3), round(b, 3)) for a, b in remain if b - a > 1e-6]
    return AllocResult(placements, rejected, free)

def result_to_dict(r: AllocResult) -> dict:
    return {
        "placements": [asdict(p) for p in r.placements],
        "rejected": [asdict(x) for x in r.rejected],
        "free_spans": [{"start_m": a, "end_m": b} for a, b in r.free_spans],
    }
