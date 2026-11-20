"""零元探索：以全悬置态（九维全 0，#9841）为原点，探查 19683 态空间的结构、
归零路径的合法性，以及两个真实标的在时间上的"离元距"。

纯本地计算，不调外部接口 —— 一次枚举 19683 个态即可穷尽。
"""
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from cognitive_being.ternary_algebra import (  # noqa: E402
    vector_to_index, hamming_distance, refinement_precedes,
)
from cognitive_being.cognitive_guard import CognitiveGuard  # noqa: E402
from cognitive_being.conservation_laws import PHASE_NAMES, PHASE_VECTORS  # noqa: E402

ZERO = [0] * 9
ZERO_IDX = vector_to_index(ZERO)


def distance_profile():
    prof = {}
    for v in itertools.product((-1, 0, 1), repeat=9):
        d = hamming_distance(list(v), ZERO)
        prof[d] = prof.get(d, 0) + 1
    return dict(sorted(prof.items()))


def phase_anchors():
    out = []
    for k in PHASE_NAMES:
        v = list(PHASE_VECTORS[k])
        out.append({
            "phase": k,
            "vector": v,
            "index": vector_to_index(v),
            "dist": hamming_distance(v, ZERO),
        })
    return out


def walk_to_zero(start, guard):
    """逐维清零，记录每次移动是否被守卫允许。"""
    cur = list(start)
    steps = []
    for i in range(9):
        if cur[i] == 0:
            continue
        nxt = cur[:]
        nxt[i] = 0
        r = guard.validate_transition(cur, nxt)
        steps.append({
            "dim": i + 1,
            "from": cur[i],
            "allowed": r.allowed,
            "violation": r.violation_type,
            "detail": r.detail,
            "state_after": nxt,
        })
        if not r.allowed:
            break
        cur = nxt
    return {
        "start": list(start),
        "start_index": vector_to_index(start),
        "start_dist": hamming_distance(start, ZERO),
        "steps": steps,
        "blocked_at_step": len(steps) if steps and not steps[-1]["allowed"] else None,
        "final_dist": hamming_distance(cur, ZERO),
    }


def main():
    guard = CognitiveGuard()
    prof = distance_profile()
    anchors = phase_anchors()

    d = json.loads((ROOT / "out" / "stock_state.json").read_text(encoding="utf-8"))
    series = {}
    for key, label in (("上证指数 000001", "sh"), ("平安银行 000001.SZ", "pab")):
        valid = [s for s in d[key]["series"] if s["valid"]]
        by_date = {s["date"]: hamming_distance(s["state"], ZERO) for s in valid}
        series[label] = by_date

    common = sorted(set(series["sh"]) & set(series["pab"]))
    payload = {
        "zero_index": ZERO_IDX,
        "total_states": sum(prof.values()),
        "distance_profile": {str(k): v for k, v in prof.items()},
        "expected_distance": 6.0,
        "anchors": anchors,
        "series": {
            "dates": common,
            "sh": [series["sh"][x] for x in common],
            "pab": [series["pab"][x] for x in common],
        },
        "walk": {
            "pab": walk_to_zero([1, 1, 0, 1, -1, 1, -1, 0, 1], guard),
            "sh": walk_to_zero([-1, -1, -1, -1, 1, -1, 1, 1, -1], guard),
        },
        "refinement": {
            "zero_precedes_pab": refinement_precedes(ZERO, [1, 1, 0, 1, -1, 1, -1, 0, 1]),
            "pab_precedes_zero": refinement_precedes([1, 1, 0, 1, -1, 1, -1, 0, 1], ZERO),
            "zero_precedes_sh": refinement_precedes(ZERO, [-1, -1, -1, -1, 1, -1, 1, 1, -1]),
            "sh_precedes_zero": refinement_precedes([-1, -1, -1, -1, 1, -1, 1, 1, -1], ZERO),
        },
    }
    (ROOT / "out" / "zero_state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("zero idx", ZERO_IDX, "| profile", prof)
    print("walk pab blocked at step", payload["walk"]["pab"]["blocked_at_step"])
    print("walk sh  blocked at step", payload["walk"]["sh"]["blocked_at_step"])
    print("series", len(common), payload["series"]["sh"][-1], payload["series"]["pab"][-1])


if __name__ == "__main__":
    main()
