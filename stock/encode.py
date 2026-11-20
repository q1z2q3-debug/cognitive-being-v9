"""
把日 K 行情映射进认知生命体 v9 的九维三态基底。

九维顺序与论文一致：[天, 地, 人, 正, 反, 合, 归, 守, 进]
每个维度只取 -1 / 0 / +1，语义在本文件 encode_day() 中逐条写明。

这是**规则编码器**，不是训练出来的模型：窗口与阈值全部固定、可复算，
不做样本外调参。它的作用是让市场状态变成 19683 个离散态里的一个对象，
而不是一段自然的文字描述。
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

DIMS = ["天", "地", "人", "正", "反", "合", "归", "守", "进"]


def load_ohlc(path: Path) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "date": r["date"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "amount": float(r["amount_yi"]),
                }
            )
    return rows


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _tail(seq: Sequence[float], n: int) -> Sequence[float]:
    return seq[max(0, len(seq) - n):]


def encode_day(rows: List[Dict[str, float]], i: int) -> Tuple[Tuple[int, ...], Dict[str, object]]:
    """返回第 i 日的九维三态向量与编码依据。

    维度语义（+1 / 0 / -1）：
      天 趋势   收盘相对 MA20：> +0.5% 上行 / < -0.5% 下行 / 其间走平
      地 量能   成交额相对 20 日均额：> 1.15 放量 / < 0.85 缩量 / 其间平量
      人 情绪   近 3 日累计收益方向：> +1% / < -1% / 其间无方向
      正 多头证据 收盘站上 MA5 且 MA5 抬升 = +1；收盘跌破 MA5 且 MA5 下压 = -1
      反 空头证据 收盘创近 10 日新低 = +1（反向力量强）；创近 10 日新高 = -1；否则 0
      合 一致性 MA5 与 MA20 同向上行 / 同向下行；交叉或平 = 0
      归 位置   收盘在近 20 日高低区间的分位：>0.8 高位（回归压力）/ <0.2 低位
      守 风险   当日振幅相对 20 日均振幅：>1.25 波动放大 = -1；<0.8 平静 = +1
      进 进攻   5 日收益 > +1.5% 且放量 = +1；< -1.5% = -1
    """
    closes = [r["close"] for r in rows[: i + 1]]
    highs = [r["high"] for r in rows[: i + 1]]
    lows = [r["low"] for r in rows[: i + 1]]
    amounts = [r["amount"] for r in rows[: i + 1]]
    cur = rows[i]["close"]

    def avg(seq, n):
        t = _tail(seq, n)
        return _mean(t)

    vec: List[int] = []
    why: Dict[str, object] = {}

    # 天：MA20 偏离
    ma20 = avg(closes, 20)
    dev = (cur / ma20 - 1) * 100
    vec.append(1 if dev > 0.5 else (-1 if dev < -0.5 else 0))
    why["天"] = f"偏离MA20 {dev:+.2f}%"

    # 地：量能比
    amt20 = avg(amounts, 20)
    vr = amounts[-1] / amt20 if amt20 else 1.0
    vec.append(1 if vr > 1.15 else (-1 if vr < 0.85 else 0))
    why["地"] = f"成交额为20日均额 {vr:.2f}x"

    # 人：3 日累计收益
    r3 = (cur / closes[-4] - 1) * 100 if len(closes) >= 4 else 0.0
    vec.append(1 if r3 > 1.0 else (-1 if r3 < -1.0 else 0))
    why["人"] = f"近3日 {r3:+.2f}%"

    # 正：站上 MA5 且 MA5 抬升
    ma5 = avg(closes, 5)
    ma5_prev = _mean(closes[-6:-1]) if len(closes) >= 6 else ma5
    if cur > ma5 and ma5 > ma5_prev:
        vec.append(1)
    elif cur < ma5 and ma5 < ma5_prev:
        vec.append(-1)
    else:
        vec.append(0)
    why["正"] = f"收盘{'>' if cur > ma5 else '<'}MA5，MA5{'抬升' if ma5 > ma5_prev else '下压'}"

    # 反：10 日新低 / 新高
    lo10 = min(lows[:-1][-10:]) if i >= 1 else lows[-1]
    hi10 = max(highs[:-1][-10:]) if i >= 1 else highs[-1]
    if cur <= lo10:
        vec.append(1)
    elif cur >= hi10:
        vec.append(-1)
    else:
        vec.append(0)
    why["反"] = f"10日区间 {lo10:.2f}–{hi10:.2f}"

    # 合：均线同向
    if ma5 > ma20 and ma5 > ma5_prev:
        vec.append(1)
    elif ma5 < ma20 and ma5 < ma5_prev:
        vec.append(-1)
    else:
        vec.append(0)
    why["合"] = f"MA5{'>' if ma5 > ma20 else '<'}MA20"

    # 归：20 日区间分位
    hi20, lo20 = max(highs[-20:]), min(lows[-20:])
    q = (cur - lo20) / (hi20 - lo20) if hi20 > lo20 else 0.5
    vec.append(1 if q < 0.2 else (-1 if q > 0.8 else 0))
    why["归"] = f"区间分位 {q:.0%}"

    # 守：振幅相对 20 日均值
    amps = []
    for j in range(max(1, i - 19), i + 1):
        prev = rows[j - 1]["close"]
        amps.append((rows[j]["high"] - rows[j]["low"]) / prev)
    if not amps:
        amps = [(rows[0]["high"] - rows[0]["low"]) / rows[0]["open"]]
    amp_now = amps[-1]
    amp_ref = statistics.median(amps) if amps else amp_now
    ar = amp_now / amp_ref if amp_ref else 1.0
    vec.append(1 if ar < 0.8 else (-1 if ar > 1.25 else 0))
    why["守"] = f"振幅为常态 {ar:.2f}x"

    # 进：5 日动量 + 量能
    r5 = (cur / closes[-6] - 1) * 100 if len(closes) >= 6 else 0.0
    if r5 > 1.5 and vr > 1.0:
        vec.append(1)
    elif r5 < -1.5:
        vec.append(-1)
    else:
        vec.append(0)
    why["进"] = f"近5日 {r5:+.2f}%"

    return tuple(vec), why
