# -*- coding: utf-8 -*-
"""
cognitive_guard.py — 认知守卫（守恒+信息单调双校验）
=====================================================
对应论文《认知生命体》§3.9 与 §5.14 的 cognitive_guard 模块。

层级边界（论文 §3.9 的关键澄清）：
  - 守卫**不**约束感知层的独立重分类（原始编码器重新归类某段文本、改变多重集，不是违规）；
  - 守卫只守在**符号演化层的 move 上**：校验提议的后继移动，合法才写入，
    非法则原地拒绝并产出一个与裂变体系同构的 `FissionSignal`。

双约束不可互相替代（论文 §3.9 / §6.1.2）：
  - 守恒合法移动中约有 33.9% 是"异号极性交换"（+1 与 -1 直接对调），
    账本完全平衡（守恒成立）却让两个已确定维度未经悬置直接翻转，违反信息单调性；
  - 因此守卫采用两级筛选：候选 move →(守恒多重集)→(信息单调)→才允许写入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta


@dataclass
class GuardResult:
    """守卫校验结果。"""
    allowed: bool
    violation_type: Optional[str] = None   # 'conservation' | 'info_monotonicity' | None
    detail: Dict = field(default_factory=dict)
    fission_signal: Optional[Dict] = None  # 非法时产出的 FissionSignal


def check_info_monotonicity(old: Sequence[int], new: Sequence[int]) -> bool:
    """候选移动是否满足信息单调性。

    检查"新状态相对旧状态"是否仅在消解旧悬置维，而不得翻转旧确定维。
    即旧 ≼ 新 的细化序关系必须成立。
    注意：悬置(消解冲突→退回0) 会破坏该序，这种"合法悬置移动"需特殊判定，
    因此这里提供的是"细化序"严格版本；守卫对合法移动用宽松版(见 validate_transition)。
    """
    return ta.refinement_precedes(old, new)


class CognitiveGuard:
    """可插拔认知守卫：在符号状态移动写入前做守恒+信息单调双校验。"""

    def __init__(self, check_block: bool = True, check_monotonic: bool = True,
                 allow_resolution_to_zero: bool = True):
        self.check_block = check_block
        self.check_monotonic = check_monotonic
        # 是否允许"确定冲突 → 消解为0"的移动（这类移动不满足严格细化序，但属合法悬置）
        self.allow_resolution_to_zero = allow_resolution_to_zero

    def validate_transition(self, old: Sequence[int],
                            new: Sequence[int]) -> GuardResult:
        """校验一次符号状态移动是否合法。

        两级筛选：
          1. 守恒：全局三元多重集不变（可选逐块多重集也不变）；
          2. 信息单调性：新状态要么是旧的细化(消解悬置)，要么把旧确定维消解为0(合法悬置)，
             但**不得**把旧确定维反转为确定值(+1↔-1 未悬置直接翻转)。
        """
        # ---- 第一级：守恒 ----
        if not cl.preserves_global_multiset(old, new):
            return GuardResult(False, "conservation",
                               {"reason": "全局三元多重集改变"})
        if self.check_block and not cl.preserves_block_multisets(old, new):
            return GuardResult(False, "conservation",
                               {"reason": "逐块三元多重集改变"})

        # ---- 第二级：信息单调性 ----
        if self.check_monotonic:
            for o, n in zip(old, new):
                if o != 0:               # 旧确定维
                    if n == -o:          # 直接反转为确定值 → 非法
                        return GuardResult(
                            False, "info_monotonicity",
                            {"reason": "已确定维度未经悬置直接翻转",
                             "dim": "index", "old": o, "new": n})
                    # n 为 0 表示消解为悬置（若允许），n==o 表示保持，均合法
            # 若禁止消解为0，则细化序必须严格成立
            if not self.allow_resolution_to_zero:
                if not ta.refinement_precedes(old, new):
                    return GuardResult(False, "info_monotonicity",
                                       {"reason": "新状态不是旧状态的证据细化"})

        return GuardResult(True, None, {"checked": True})

    def apply_guarded_move(self, old: Sequence[int],
                           new: Sequence[int],
                           source: str = "symbolic") -> Tuple[Sequence[int], GuardResult]:
        """带守卫写入：合法才采纳新状态，非法则拒绝并产出 FissionSignal。

        返回 (最终状态, 校验结果)。非法时最终状态=old（原地拒绝）。
        """
        res = self.validate_transition(old, new)
        if res.allowed:
            return tuple(new), res
        res.fission_signal = {
            "type": "cognitive_consistency",   # 第八类信号（并入L7裂变检测）
            "severity": "WARN",
            "source": source,
            "detail": {"old": tuple(old), "proposed": tuple(new),
                       "violation": res.violation_type},
        }
        return tuple(old), res


# ---------------------------------------------------------------------------
# 统计：守恒合法移动中违反信息单调性的占比（论文 §3.9：约33.9%）
# ---------------------------------------------------------------------------

def stat_polarity_exchange_ratio(max_states: int = 5000, seed: int = 1) -> Dict:
    """在部分状态上统计：守恒合法移动中，异号极性交换(违反信息单调)的占比。

    论文报告约 33.9%。这里对采样的状态做全合法后继统计，结果应接近该量级。
    """
    import random
    rng = random.Random(seed)
    total_moves = 0
    violating = 0
    states = [ta.index_to_vector(i) for i in range(ta.NUM_STATES)]
    sample = rng.sample(states, min(max_states, ta.NUM_STATES))
    guard = CognitiveGuard(check_block=False, check_monotonic=True)
    for st in sample:
        for move in cl.legal_moves(st):
            total_moves += 1
            res = guard.validate_transition(st, move)
            if not res.allowed and res.violation_type == "info_monotonicity":
                violating += 1
    ratio = violating / total_moves if total_moves else 0.0
    return {"total_legal_moves": total_moves, "info_monotonic_violations": violating,
            "ratio": ratio}
