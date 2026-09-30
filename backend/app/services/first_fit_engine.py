"""1D First-Fit stall placement along a street segment.

Stalls cannot cross pillars. When a segment has power outlets, a stall's
closed interval [start_m, end_m] must be fully covered by at least one
outlet's service interval [position_m - radius_m, position_m + radius_m];
covering only the midpoint (one end outside) is rejected.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

EPS = 1e-9

REASON_NO_SPACE = "无连续空档可放下且不跨越挡柱"
REASON_NO_POWER = "供电不足：摊位起止区间未被任一供电桩的服务区间完全覆盖"

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

def interval_covered(start_m: float, end_m: float, outlets: list[dict]) -> bool:
    """True iff the closed interval [start_m, end_m] is fully contained in at
    least one outlet service interval. Covering only the midpoint fails."""
    for o in outlets:
        serve_lo = o["position_m"] - o["radius_m"]
        serve_hi = o["position_m"] + o["radius_m"]
        if start_m + EPS >= serve_lo and end_m <= serve_hi + EPS:
            return True
    return False

def _earliest_covered_start(cursor: float, span_end: float, need: float,
                            outlets: list[dict]) -> float | None:
    """Earliest start >= cursor within the span where [start, start+need] is
    fully covered by a single outlet. None if no such position exists."""
    best: float | None = None
    latest_start = span_end - need
    for o in outlets:
        lo = max(cursor, o["position_m"] - o["radius_m"])
        hi = min(latest_start, o["position_m"] + o["radius_m"] - need)
        if lo <= hi + EPS:
            if best is None or lo < best:
                best = lo
    return best

def allocate_first_fit(width_m: float, vendors: list[dict], pillars: list[dict],
                       outlets: list[dict] | None = None) -> AllocResult:
    """vendors sorted by priority ascending then id.

    Each stall needs stall_width_m contiguous metres inside one free span
    (no pillar cross). When outlets are configured, the stall's closed
    interval must additionally be fully covered by one outlet's service
    interval. Rejection reasons are mutually exclusive: no contiguous space
    (cross-pillar/insufficient gap) or insufficient power coverage.
    With no outlets configured the segment behaves like the green-field case.
    """
    outlets = outlets or []
    spans = free_spans_from_pillars(width_m, pillars)
    # mutable remaining capacity per span
    remain = [[a, b] for a, b in spans]
    ordered = sorted(vendors, key=lambda v: (v.get("priority", 1), v["id"]))
    placements: list[Placement] = []
    rejected: list[Rejected] = []
    for v in ordered:
        need = float(v["stall_width_m"])
        start: float | None = None
        span_idx = -1
        for i, span in enumerate(remain):
            if span[1] - span[0] + EPS < need:
                continue
            if not outlets:
                start, span_idx = span[0], i
                break
            cand = _earliest_covered_start(span[0], span[1], need, outlets)
            if cand is not None:
                start, span_idx = cand, i
                break
        if start is None:
            # Mutually exclusive reasons: if any span geometrically had room,
            # the failure is coverage; otherwise it is space/pillar related.
            has_space = any(span[1] - span[0] + EPS >= need for span in remain)
            reason = REASON_NO_POWER if (has_space and outlets) else REASON_NO_SPACE
            rejected.append(Rejected(v["id"], v["name"], need, reason))
            continue
        end = start + need
        placements.append(Placement(v["id"], v["name"], round(start, 3), round(end, 3), need))
        remain[span_idx][0] = end
    free = [(round(a, 3), round(b, 3)) for a, b in remain if b - a > 1e-6]
    return AllocResult(placements, rejected, free)

def result_to_dict(r: AllocResult) -> dict:
    return {
        "placements": [asdict(p) for p in r.placements],
        "rejected": [asdict(x) for x in r.rejected],
        "free_spans": [{"start_m": a, "end_m": b} for a, b in r.free_spans],
    }
