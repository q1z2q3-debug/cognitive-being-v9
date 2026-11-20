# -*- coding: utf-8 -*-
"""
suspension_decision.py — Bayes最优悬置（三支决策）
===================================================
对应论文《认知生命体》§3.7 与 §5.13 的 suspension_decision 模块。

核心内容：
  1. 三动作代价模型：承诺阳性 POS(+1)、承诺阴性 NEG(-1)、悬置 SUS(0)；
  2. (α, β) 阈值推导与决策粗糙集三支决策；
  3. Bayes 最优动作选择（最小期望风险）；
  4. 非对称三值量化（TTQ式，正向/负向不同尺度）；
  5. Triple Barrier 仓位映射（金融场景对接）。

数学（论文 §3.7）：
  R(POS)=λ_FP(1-p),  R(NEG)=λ_FN·p,  R(SUS)=λ_abstain；
  p≥α ⇒ POS；p≤β ⇒ NEG；β<p<α ⇒ BND(悬置)。
  该机制与 Chow 最优弃权(selective prediction)同源：以放弃覆盖率换取承诺精度。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class SuspensionCosts:
    """三动作代价模型参数。

    Attributes:
        lambda_fp:   误趋代价（承诺阳性但实际为负）
        lambda_fn:   误避代价（承诺阴性但实际为正）
        lambda_abstain: 悬置(弃权)代价
    """
    lambda_fp: float = 1.0
    lambda_fn: float = 1.0
    lambda_abstain: float = 0.4

    # 决策粗糙集(DTRS)的中间收益/代价（可选，默认对称）
    lambda_abstain_neg: float = 0.4   # 本应悬置却承诺阴性的代价
    lambda_abstain_pos: float = 0.4   # 本应悬置却承诺阳性的代价
    lambda_tp: float = 0.0            # 正确承诺阳性的收益（负代价）
    lambda_tn: float = 0.0            # 正确承诺阴性的收益

    def thresholds(self) -> Tuple[float, float]:
        """计算 (α, β) 决策阈值。

        α = (λ_FP − λ_abstain,neg) / [(λ_FP − λ_abstain,neg) + (λ_abstain,pos − λ_TP)]
        β = (λ_abstain,neg − λ_TN) / [(λ_abstain,neg − λ_TN) + (λ_FN − λ_abstain,pos)]
        """
        num_a = self.lambda_fp - self.lambda_abstain_neg
        den_a = (self.lambda_fp - self.lambda_abstain_neg) + (self.lambda_abstain_pos - self.lambda_tp)
        alpha = num_a / den_a if den_a != 0 else 0.5

        num_b = self.lambda_abstain_neg - self.lambda_tn
        den_b = (self.lambda_abstain_neg - self.lambda_tn) + (self.lambda_fn - self.lambda_abstain_pos)
        beta = num_b / den_b if den_b != 0 else 0.5
        return alpha, beta

    def risk(self, action: int, p: float) -> float:
        """三动作的期望风险。action∈{+1,-1,0}。"""
        if action == 1:
            return self.lambda_fp * (1 - p)
        if action == -1:
            return self.lambda_fn * p
        return self.lambda_abstain


def bayes_optimal_action(p: float, costs: SuspensionCosts = SuspensionCosts()) -> int:
    """给定阳性后验 p，返回 Bayes 最优三支动作：+1 / -1 / 0。"""
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"后验概率必须在[0,1]，收到 {p}")
    r_pos = costs.risk(1, p)
    r_neg = costs.risk(-1, p)
    r_sus = costs.risk(0, p)
    # 最小期望风险；悬置平局时优先悬置（保守）
    best = 0
    best_r = r_sus
    if r_pos < best_r:
        best, best_r = 1, r_pos
    if r_neg < best_r:
        best, best_r = -1, r_neg
    return best


def three_way_decision(p: float, costs: SuspensionCosts = SuspensionCosts()) -> Dict[str, object]:
    """三支决策：返回动作、所在区域(REG/NEG/BND)与 (α,β)。"""
    alpha, beta = costs.thresholds()
    if p >= alpha:
        action, region = 1, "POS"
    elif p <= beta:
        action, region = -1, "NEG"
    else:
        action, region = 0, "BND"
    return {"action": action, "region": region, "p": p, "alpha": alpha, "beta": beta}


# ---------------------------------------------------------------------------
# 非对称三值量化（TTQ式）
# ---------------------------------------------------------------------------

def asymmetric_quantize(z: float, pos_scale: float = 1.0, neg_scale: float = 1.0,
                        pos_thresh: float = 0.5, neg_thresh: float = 0.5) -> int:
    """非对称三值量化：允许正向与负向使用不同尺度/阈值。

    用于神经前端输出 z 的量化（论文 §3.7 提到的 TTQ 式非对称量化）。
    """
    if z > pos_thresh:
        return 1
    if z < -neg_thresh:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Triple Barrier 仓位映射（金融对接，论文 §3.7）
# ---------------------------------------------------------------------------

@dataclass
class PositionResult:
    position: int            # +1满仓 / -1离场 / 0减半观望
    meta_label: str          # 'LONG' / 'SHORT' / 'HOLD_HALF'
    action: int              # 认知层原始三值动作
    prob: float
    half_notional: float     # 悬置时减半的仓位比例（0.5）


def triple_barrier_position(action: int, p: float,
                            half_notional: float = 0.5) -> PositionResult:
    """三值认知动作 → Triple Barrier 仓位。

    规则（论文 §3.7）：阳性满仓(+1)，阴性离场(-1)，悬置减半观望(0.5)并给出 meta-label。
    """
    if action == 1:
        return PositionResult(position=1, meta_label="LONG", action=1,
                              prob=p, half_notional=1.0)
    if action == -1:
        return PositionResult(position=-1, meta_label="SHORT", action=-1,
                              prob=p, half_notional=0.0)
    return PositionResult(position=0, meta_label="HOLD_HALF", action=0,
                          prob=p, half_notional=half_notional)


# ---------------------------------------------------------------------------
# 示例：默认对称代价下的 (α, β)
# ---------------------------------------------------------------------------

def default_thresholds() -> Tuple[float, float]:
    """默认对称代价(λ=1.0, λ_abstain=0.4)下的阈值示例。"""
    c = SuspensionCosts(lambda_fp=1.0, lambda_fn=1.0, lambda_abstain=0.4)
    return c.thresholds()
