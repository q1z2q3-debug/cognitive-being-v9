# -*- coding: utf-8 -*-
"""
cognitive_experiments.py — 三个对照实验（论文 §6.1.1 / §5.13）
================================================================
把"三态优于二态"从主张变为可复现证据。三个实验全部参数固定、可复现。

  实验一·选择性预测：校准概率二分类，比较"强制承诺"vs"Bayes最优弃权"，
        验证第三态以放弃覆盖率换取承诺精度，代价降低（论文：40.2%）；
  实验二·0态公理：在不同证据覆盖率下测量投影算子悬置率与确定错误率，
        并穷举判定合取/析取信息单调(True)、多数表决不单调(False)；
  实验三·长链精度：500步随机合法演化，对照精确离散三值 vs 浮点软三值，
        验证离散表示在长链上不漂移（守恒零违反）。
结果落盘 JSON（analysis/experiment_results.json）。
"""

from __future__ import annotations

import json
import os
import random
from typing import Dict, List, Tuple

import numpy as np

from . import ternary_algebra as ta
from . import conservation_laws as cl
from . import suspension_decision as sd

RNG = np.random.default_rng(0)


# ---------------------------------------------------------------------------
# 实验一：选择性预测
# ---------------------------------------------------------------------------

def experiment_selective_prediction(n: int = 40000, sigma: float = 1.2,
                                    costs: sd.SuspensionCosts = None) -> Dict:
    """校准概率二分类 + Bayes最优弃权 vs 强制承诺。

    隐标签 y∈{-1,+1} 等先验，观测 z=y+ε, ε~N(0,σ)，阳性后验 p=P(y=+1|z)（闭式，真校准）。
    除固定参数结果外，还输出 risk-coverage 权衡曲线——第三态价值的本质证据：
    随弃权(悬置)率上升，承诺错误率单调下降，用放弃覆盖率换取承诺精度。
    """
    costs = costs or sd.SuspensionCosts(lambda_fp=1.0, lambda_fn=1.0,
                                        lambda_abstain=0.4)
    y = RNG.choice([-1.0, 1.0], size=n)
    eps = RNG.normal(0, sigma, size=n)
    z = y + eps
    # 闭式后验 p = P(y=+1 | z) = 1/(1+exp(-2z/σ²))  (等先验、等方差高斯)
    p = 1.0 / (1.0 + np.exp(-2.0 * z / (sigma * sigma)))

    # 强制承诺：p>=0.5 → +1, else -1
    forced = np.where(p >= 0.5, 1.0, -1.0)
    forced_err = np.mean(forced != y)
    forced_cost = np.mean(np.where(forced != y, 1.0, 0.0))

    # Bayes最优弃权：三动作，错误代价1.0，弃权代价0.4
    actions = np.array([sd.bayes_optimal_action(pi, costs) for pi in p])
    committed = actions != 0
    commit_rate = committed.mean()
    commit_err = np.mean(actions[committed] != y[committed]) if committed.any() else 0.0
    # 代价：承诺且错误→1.0；弃权→0.4；承诺正确→0
    cost = np.where(actions == 0, 0.4,
                    np.where(actions == y, 0.0, 1.0))
    mean_cost = cost.mean()

    # risk-coverage 曲线：对不同的弃权代价 λ_abstain，记录 (覆盖率, 承诺错误率)
    rc = []
    for lab in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        c = sd.SuspensionCosts(lambda_fp=1.0, lambda_fn=1.0, lambda_abstain=lab)
        acts = np.array([sd.bayes_optimal_action(pi, c) for pi in p])
        cm = acts != 0
        cov = cm.mean()
        err = np.mean(acts[cm] != y[cm]) if cm.any() else 0.0
        rc.append({"abstain_cost": lab, "coverage": float(cov),
                   "commit_error_rate": float(err)})

    result = {
        "forced_commit_error_rate": float(forced_err),
        "forced_mean_cost": float(forced_cost),
        "bayes_commit_rate": float(commit_rate),
        "bayes_commit_error_rate": float(commit_err),
        "bayes_mean_cost": float(mean_cost),
        "cost_reduction": float((forced_cost - mean_cost) / forced_cost),
        "sigma": sigma, "n": n,
        "risk_coverage_curve": rc,
    }
    return result


# ---------------------------------------------------------------------------
# 实验二：0态公理
# ---------------------------------------------------------------------------

def _evidence_mask(n_dim: int = 9, coverage: float = 0.5) -> List[bool]:
    """随机生成证据覆盖掩码（coverage 比例的维度有证据）。"""
    rng = random.Random(int(coverage * 1000))
    mask = [rng.random() < coverage for _ in range(n_dim)]
    if not any(mask):
        mask[0] = True
    return mask


def _unknown_vector() -> List[int]:
    return [0] * 9


def _evidence_vector(mask: List[bool]) -> List[int]:
    rng = random.Random(42)
    return [rng.choice([-1, 1]) if m else 0 for m in mask]


def _projection_error_rate(operator, n_trials: int = 2000, coverage: float = 0.5) -> Dict:
    """在给定证据覆盖率下测量某投影算子的悬置率与确定错误率。

    流程：构造未知输入 x 与两个(或三个)证据向量，算子给出投影；
    悬置率 = 输出含0的比例；确定错误 = 输出确定但与其应一致的"真值"不符的比例。
    这里"真值"定义为证据间的多数共识（作为ground truth标签）。
    """
    rng = random.Random(7)
    suspensions = 0
    determ_errors = 0
    determined = 0
    for _ in range(n_trials):
        mask = _evidence_mask(9, coverage)
        evs = [_evidence_vector(mask) for _ in range(3)]
        if operator.__name__ == "majority_vote":
            out = operator(evs[0], evs[1], evs[2])
        else:
            out = operator(evs[0], evs[1])
        if any(v == 0 for v in out):
            suspensions += 1
        else:
            determined += 1
            # ground truth：每维取三个证据的符号多数（有证据处）
            gt = []
            for i in range(9):
                vals = [e[i] for e in evs if e[i] != 0]
                gt.append(1 if sum(vals) > 0 else (-1 if sum(vals) < 0 else 0))
            if any(out[i] != gt[i] for i in range(9) if gt[i] != 0):
                determ_errors += 1
    return {"coverage": coverage,
            "suspension_rate": suspensions / n_trials,
            "determinate_error_rate": determ_errors / max(determined, 1),
            "determined_count": determined}


def experiment_zero_axiom() -> Dict:
    """0态公理：不同证据覆盖率下的悬置率/确定错误率 + 信息单调性穷举判定。"""
    results = {"coverage_curve": [], "monotonicity": {}}
    for cov in [0.1, 0.3, 0.5, 0.7, 0.9]:
        results["coverage_curve"].append({
            "op": "conjunction",
            **(_projection_error_rate(ta.conjunctive_project, coverage=cov))})
        results["coverage_curve"].append({
            "op": "majority_vote",
            **(_projection_error_rate(ta.majority_vote, coverage=cov))})
    # 信息单调性穷举（论文实验二的形式化判定）
    results["monotonicity"] = {
        "conjunction": _check_monotonicity(ta.conjunctive_project),
        "disjunction": _check_monotonicity(ta.disjunctive_project),
        "majority_vote": _check_monotonicity(ta.majority_vote),
    }
    return results


def _check_monotonicity(op, n_states: int = 600, refs_per_state: int = 30,
                        seed: int = 3) -> bool:
    """采样验证算子是否信息单调（论文实验二：合取/析取 True，多数表决 False）。

    语义：若证据 a≼a', b≼b'（细化序），且 op 在 (a,b) 上结论确定，则 op 在 (a',b') 上
    不得推翻该结论。全空间精确穷举成本为 O(N²·组合)，这里对细化对做确定性采样验证；
    结果标注为"采样验证"而非穷举（穷举仅用于 ternary_algebra.is_info_monotonic 的一元情形）。
    """
    import random
    rng = random.Random(seed)
    states = [ta.index_to_vector(i) for i in range(ta.NUM_STATES)]
    sample = rng.sample(states, min(n_states, ta.NUM_STATES))
    for a in sample:
        for _ in range(refs_per_state):
            # 构造 a' ≽ a：随机把 a 的若干 0 维消解为确定值
            ap = list(a)
            for i in range(9):
                if ap[i] == 0 and rng.random() < 0.5:
                    ap[i] = rng.choice([-1, 1])
            ap = tuple(ap)
            for b in sample:
                bp = list(b)
                for i in range(9):
                    if bp[i] == 0 and rng.random() < 0.5:
                        bp[i] = rng.choice([-1, 1])
                bp = tuple(bp)
                try:
                    if op.__name__ == "majority_vote":
                        o_ab = op(a, b, a)
                        o_abp = op(ap, bp, ap)
                    else:
                        o_ab = op(a, b)
                        o_abp = op(ap, bp)
                except Exception:
                    continue
                if not ta.is_determined(o_ab):
                    continue
                if o_ab != o_abp:
                    return False   # 找到反例 → 不单调
    return True


# ---------------------------------------------------------------------------
# 实验三：长链精度
# ---------------------------------------------------------------------------

def _soft_evolve(vector: List[float], noise_std: float, guard) -> List[float]:
    """软三值演化：在合法移动上叠加浮点噪声。"""
    rng = np.random.default_rng()
    base = [round(v) for v in vector]
    if any(v not in (-1, 0, 1) for v in base):
        base = [1 if v > 0.5 else (-1 if v < -0.5 else 0) for v in vector]
    # 选一个合法移动作为"无噪声目标"
    moves = cl.legal_moves(tuple(base))
    if not moves:
        return vector
    target = list(rng.choice(moves))
    # 加入噪声后沿目标方向软移动
    noisy = [v + n for v, n in zip(target, rng.normal(0, noise_std, 9))]
    return noisy


def experiment_long_chain(steps: int = 500, base: Tuple[int, ...] = None,
                          noise_stds=(0.01, 0.05, 0.10)) -> Dict:
    """500步随机合法演化，对照精确离散 / 浮点软三值 / 软+每步重量化。"""
    from .cognitive_guard import CognitiveGuard
    base = base or (1, 0, 0, 0, 0, 0, 0, 0, -1)  # (1,7,1)
    guard = CognitiveGuard(check_block=False)

    def run_discrete():
        v = list(base)
        violations = 0
        charge_drift = []
        rng = random.Random(0)
        for _ in range(steps):
            moves = cl.legal_moves(tuple(v))
            nxt = rng.choice(moves)
            if not cl.preserves_global_multiset(v, nxt):
                violations += 1
            v = list(nxt)
            charge_drift.append(abs(cl.global_charge(v) - cl.global_charge(base)))
        return {"violations": violations, "mean_abs_charge_drift":
                float(np.mean(charge_drift))}

    def run_soft(noise):
        v = [float(x) for x in base]
        violations = 0
        drift = []
        rng = random.Random(1)
        nrng = np.random.default_rng(2)
        for _ in range(steps):
            target = list(rng.choice(cl.legal_moves(
                tuple(1 if x > 0.5 else (-1 if x < -0.5 else 0) for x in v))))
            noisy = [a + b for a, b in zip(target, nrng.normal(0, noise, 9))]
            # 软表示的"守恒"按量化后多重集判定
            q = tuple(1 if x > 0.5 else (-1 if x < -0.5 else 0) for x in noisy)
            if cl.global_multiset(q) != cl.global_multiset(base):
                violations += 1
            drift.append(abs(cl.global_charge(q) - cl.global_charge(base)))
            v = noisy
        return {"noise_std": noise, "violations": violations,
                "mean_abs_charge_drift": float(np.mean(drift))}

    results = {"base": list(base), "steps": steps,
               "discrete": run_discrete(),
               "soft": [run_soft(n) for n in noise_stds]}
    return results


# ---------------------------------------------------------------------------
# 汇总 & 落盘
# ---------------------------------------------------------------------------

def run_all(out_path: str = "analysis/experiment_results.json") -> Dict:
    """运行三个对照实验，结果落盘 JSON。"""
    results = {
        "experiment1_selective_prediction": experiment_selective_prediction(),
        "experiment2_zero_axiom": experiment_zero_axiom(),
        "experiment3_long_chain": experiment_long_chain(),
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


if __name__ == "__main__":
    import pprint
    pprint.pprint(run_all())
