"""
把上证 / 沪深300 的日 K 序列跑进认知生命体 v9 的三值状态空间。

两条路径严格分开（这是落库时踩过坑的边界）：
  观测路径  absorb_evidence —— 每日行情是外部事实，直接采纳，不经守卫；
  诊断路径  CognitiveGuard.validate_transition —— 只用来观察"今天的证据是否在
            推翻昨天已确立的判断"，是诊断指标，不用于裁决。

用法（在仓库根目录）：
    python -m stock.run
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cognitive_being import conservation_laws as cl  # noqa: E402
from cognitive_being import ternary_algebra as ta  # noqa: E402
from cognitive_being.cognitive_guard import CognitiveGuard  # noqa: E402

from stock.encode import DIMS, encode_day, load_ohlc  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"

NAME_MAP = {
    "sh000001.csv": "上证指数 000001",
    "sh000300.csv": "沪深300 000300",
    "sz000001_pab.csv": "平安银行 000001.SZ",
    "sh601166_xy.csv": "兴业银行 601166.SH",
    "sh600000_pf.csv": "浦发银行 600000.SH",
    "sh600016_ms.csv": "民生银行 600016.SH",
    "sh601818_gd.csv": "光大银行 601818.SH",
    "sh600015_hx.csv": "华夏银行 600015.SH",
    "sh601169_bj.csv": "北京银行 601169.SH",
}
OUT = Path(__file__).resolve().parent / "out"

PHASE_CN = {
    "accumulate": "积聚",
    "transform_a": "转化A",
    "decay": "衰减",
    "transform_b": "转化B",
}


def _amplitude(rows, i: int) -> float:
    prev = rows[i - 1]["close"] if i >= 1 else rows[i]["open"]
    return (rows[i]["high"] - rows[i]["low"]) / prev


def tension(rows, i: int, hamming_step: int) -> Dict[str, float]:
    """把论文的张力公式（0.4 负荷 + 0.3 压力 + 0.3 波动）映射到市场量。

    这是映射，不是论文原义：论文的 task_load 指任务负荷，这里换成波动负荷。
    """
    amps = [_amplitude(rows, j) for j in range(max(1, i - 19), i + 1)]
    if not amps:
        amps = [_amplitude(rows, 0)]
    ref = sorted(amps)[len(amps) // 2] or 0.01
    load = min(1.0, _amplitude(rows, i) / ref)

    closes = [r["close"] for r in rows[: i + 1]]
    ma20 = sum(closes[-20:]) / len(closes[-20:])
    drop = max(0.0, (ma20 - rows[i]["close"]) / ma20)
    pressure = min(1.0, drop / 0.03)

    flux = min(1.0, hamming_step / 9)
    return {
        "task_load": round(load, 3),
        "context_pressure": round(pressure, 3),
        "stability_flux": round(flux, 3),
        "T": round(0.4 * load + 0.3 * pressure + 0.3 * flux, 3),
    }


def market_regime(vec: Sequence[int]) -> str:
    """市场态判据：按定向度与悬置率分类。

    不用论文四象的汉明最近邻——四个相位向量都含大量 +1，
    对"全负"的市场向量会全部误判为"积聚"。这里改用可观测计数，
    并明确它是工程映射，不是论文相位。
    """
    pos = sum(1 for x in vec if x == 1)
    neg = sum(1 for x in vec if x == -1)
    zero = 9 - pos - neg
    if zero >= 5:
        return "悬置主导"
    if neg >= 5 and neg - pos >= 3:
        return "空头确立"
    if pos >= 5 and pos - neg >= 3:
        return "多头确立"
    if pos >= 3 and neg >= 3:
        return "多空对峙"
    return "弱定向"


def run_symbol(name: str, csv_path: Path, warmup: int = 5) -> Dict:
    rows = load_ohlc(csv_path)
    guard = CognitiveGuard()
    state: Tuple[int, ...] = (0,) * 9
    prev_obs: Tuple[int, ...] | None = None
    series: List[Dict] = []

    for i in range(len(rows)):
        obs, why = encode_day(rows, i)
        valid = i >= warmup
        prev = state

        flips = 0
        if valid:
            if prev_obs is not None:
                flips = sum(1 for a, b in zip(prev_obs, obs) if a * b == -1)
            state = ta.absorb_evidence(prev, obs)

        step = ta.hamming_distance(prev, state) if valid else 0
        if valid:
            res = guard.validate_transition(prev, state)
            diag = {
                "allowed": res.allowed,
                "violation": res.violation_type,
                "conservation_ok": cl.preserves_global_multiset(prev, state),
            }
        else:
            diag = {"allowed": True, "violation": None, "conservation_ok": True}

        series.append(
            {
                "date": rows[i]["date"],
                "close": rows[i]["close"],
                "valid": valid,
                "obs": list(obs),
                "obs_str": ta.vector_tostring(obs) if valid else "warmup",
                "state": list(state),
                "state_str": ta.vector_tostring(state),
                "index": ta.vector_to_index(state),
                "regime": market_regime(state),
                "phase": cl.locate_phase(state),
                "phase_cn": PHASE_CN.get(cl.locate_phase(state), "?"),
                "group27": list(ta.project_to_27(state)),
                "hamming_step": step,
                "flips": flips,
                "tension": tension(rows, i, step),
                "diag": diag,
                "why": why,
            }
        )
        if valid:
            prev_obs = obs

    valid_rows = [s for s in series if s["valid"]]
    counts = {"conservation": 0, "info_monotonicity": 0}
    for s in valid_rows:
        v = s["diag"]["violation"]
        if v in counts:
            counts[v] += 1

    first, last = valid_rows[0], valid_rows[-1]
    ret = (last["close"] / first["close"] - 1) * 100

    return {
        "symbol": name,
        "bars": len(series),
        "effective_bars": len(valid_rows),
        "warmup_bars": len(series) - len(valid_rows),
        "dim_names": DIMS,
        "series": series,
        "summary": {
            "first_date": first["date"],
            "last_date": last["date"],
            "first_close": first["close"],
            "last_close": last["close"],
            "period_return_pct": round(ret, 2),
            "last_obs": last["obs"],
            "last_obs_str": last["obs_str"],
            "last_state": last["state"],
            "last_state_str": last["state_str"],
            "last_index": last["index"],
            "last_regime": last["regime"],
            "last_phase": last["phase_cn"],
            "last_group27": last["group27"],
            "tension": last["tension"],
            "determined_dims": sum(1 for x in last["obs"] if x != 0),
            "suspended_dims": sum(1 for x in last["obs"] if x == 0),
            "obs_direct_flips": sum(s["flips"] for s in valid_rows),
            "state_direct_flips": counts["info_monotonicity"],
            "conservation_breaks": counts["conservation"],
            "regime_path": [
                {"date": s["date"], "regime": s["regime"]} for s in valid_rows
            ],
            "tension_path": [
                {"date": s["date"], "T": s["tension"]["T"]} for s in valid_rows
            ],
        },
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    wanted = sys.argv[1:]
    targets = [
        (NAME_MAP.get(f.name, f.stem), f)
        for f in sorted(DATA.glob("*.csv"))
        if not wanted or f.name in wanted or f.stem in wanted
    ]
    results = {}

    for name, path in targets:
        r = run_symbol(name, path)
        results[name] = r
        print(f"\n=== {name} ===")
        print(f"{'date':<10}{'close':>10}  {'九维观测':<20}{'累积态':<20}{'态':<8}{'张力':>6}")
        for s in r["series"][-7:]:
            print(
                f"{s['date']:<10}{s['close']:>10.2f}  {s['obs_str']:<20}"
                f"{s['state_str']:<20}{s['regime']:<8}{s['tension']['T']:>6.2f}"
            )
        sm = r["summary"]
        print(f"\n有效区间 {sm['first_date']}–{sm['last_date']}（{r['effective_bars']} 日，"
              f"预热 {r['warmup_bars']} 日）累计 {sm['period_return_pct']:+.2f}%")
        print(f"最新观测 {sm['last_obs_str']}  累积态 {sm['last_state_str']}  索引 #{sm['last_index']}")
        print(f"市场态 {sm['last_regime']}  张力 {sm['tension']['T']}  "
              f"确定 {sm['determined_dims']}/9  悬置 {sm['suspended_dims']}/9")
        print(f"观测层直接翻转 {sm['obs_direct_flips']} 维次；"
              f"累积态直接翻转 {sm['state_direct_flips']} 次；"
              f"守恒打破 {sm['conservation_breaks']} 次")

    (OUT / "stock_state.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n写出 {OUT / 'stock_state.json'}")


if __name__ == "__main__":
    main()
