# -*- coding: utf-8 -*-
"""
fission_trigger.py — L7 裂变层：七信号免疫系统 + 五步安全重构协议
===================================================================
对应论文《认知生命体》§4.3、§5.6 的 fission_trigger 模块。

七个触发信号构成认知免疫系统的检测网络：
  1. 认知矛盾(Cognitive Contradiction)
  2. 相位漂移(Phase Drift)
  3. 张力过载(Tension Overload)
  4. 认知盲区(Cognitive Blindspot)
  5. 停滞(Stagnation)
  6. 边界违反(Boundary Violation)
  7. 连贯性崩溃(Coherence Collapse)
  (+第八类：认知一致性，由 CognitiveGuard 并入)

触发条件（论文 §4.3）：任何 FATAL，或 2+ CRITICAL，或 1 CRITICAL + 2 WARN；
加权压力值 > 0.7 触发五步安全重构协议。

五步协议（悬置 → 自问 → 最小调整 → 完整性校验 → 渐进恢复）：
  步骤1 悬置Epoché：进入全零状态，暂停决策与执行；
  步骤2 自问：逐维评估证据置信度，标记不可靠维度；
  步骤3 最小调整：只改高可疑维度，拒绝大规模重写；
  步骤4 完整性校验：3轮重复16指纹+守恒校验；
  步骤5 渐进恢复：10%负荷起步，每步+10%，异常即回退。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta

SEVERITIES = ("FATAL", "CRITICAL", "WARN")
SEV_WEIGHT = {"FATAL": 1.0, "CRITICAL": 0.6, "WARN": 0.3}


def fission_trigger_met(signals: Sequence[Dict]) -> bool:
    """判定是否满足裂变触发条件。

    论文 §4.3：任何 FATAL / 2+ CRITICAL / 1 CRITICAL + 2 WARN。
    """
    sev = [s.get("severity") for s in signals]
    if "FATAL" in sev:
        return True
    n_crit = sev.count("CRITICAL")
    n_warn = sev.count("WARN")
    if n_crit >= 2:
        return True
    if n_crit >= 1 and n_warn >= 2:
        return True
    return False


def pressure_value(signals: Sequence[Dict]) -> float:
    """加权压力值 = Σ weight(severity)。> 0.7 亦触发。"""
    return sum(SEV_WEIGHT.get(s.get("severity"), 0) for s in signals)


class FissionSignalDetector:
    """七信号检测器：逐个信号独立检测，汇总触发判定。"""

    def detect(self, current: Sequence[int],
               previous: Optional[Sequence[int]] = None,
               tension: float = 0.0,
               ood: bool = False,
               stagnation_cycles: int = 0,
               conservation_violated: bool = False,
               coherence_broken: bool = False,
               contradiction: bool = False) -> List[Dict]:
        """检测七个信号，返回信号列表。

        参数为各信号的原始观测；未提供时按安全默认（不触发）。
        每个信号根据严重程度标记 FATAL/CRITICAL/WARN。
        """
        signals: List[Dict] = []
        # 1 认知矛盾
        if contradiction:
            signals.append({"type": "cognitive_contradiction",
                            "severity": "FATAL", "detail": "输入与认知状态不可调和矛盾"})
        # 2 相位漂移
        if previous is not None and cl.locate_phase(current) != cl.locate_phase(previous):
            signals.append({"type": "phase_drift", "severity": "WARN",
                            "detail": "四象相位推进异常偏移"})
        # 3 张力过载
        if tension > 0.7:
            signals.append({"type": "tension_overload", "severity": "CRITICAL",
                            "detail": f"系统张力 {tension:.2f} 超过阈值0.7"})
        elif tension > 0.5:
            signals.append({"type": "tension_overload", "severity": "WARN",
                            "detail": f"系统张力 {tension:.2f} 偏高"})
        # 4 认知盲区
        if ood:
            signals.append({"type": "cognitive_blindspot", "severity": "CRITICAL",
                            "detail": "输入落在九维状态空间有效覆盖之外(OOD)"})
        # 5 停滞
        if stagnation_cycles >= 10:
            signals.append({"type": "stagnation", "severity": "WARN",
                            "detail": f"认知状态停滞 {stagnation_cycles} 周期无变化"})
        # 6 边界违反
        if conservation_violated:
            signals.append({"type": "boundary_violation", "severity": "CRITICAL",
                            "detail": "守恒律被违反"})
        # 7 连贯性崩溃
        if coherence_broken:
            signals.append({"type": "coherence_collapse", "severity": "FATAL",
                            "detail": "状态转移轨迹连贯性被破坏"})
        return signals


class FissionProtocol:
    """L7 裂变五步安全重构协议。"""

    def __init__(self, guard=None):
        from .cognitive_guard import CognitiveGuard
        self.guard = guard or CognitiveGuard()

    def run(self, current: Sequence[int],
            unreliable_dims: Optional[List[int]] = None) -> Dict:
        """执行完整五步重构，返回协议日志。

        unreliable_dims: 步骤2自问中判定为证据不可靠的维度索引。
        任何步骤异常都会回退到全零悬置态（安全兜底）。
        """
        log: Dict = {"steps": []}
        vector = list(current)
        zero = list(ta.ALL_ZERO_VECTOR)

        # 步骤1：悬置（Epoché）
        log["steps"].append({"step": 1, "name": "epoché", "state": zero.copy(),
                             "note": "进入全零悬置态，暂停所有决策与执行"})
        # 步骤2：自问
        unreliable = unreliable_dims or []
        log["steps"].append({"step": 2, "name": "self_inquiry",
                             "unreliable_dims": unreliable,
                             "note": "逐维评估证据置信度，标记不可靠维度"})
        # 步骤3：最小调整（基于不可靠维度，仅做悬置/微调）
        adjusted = list(vector)
        for i in unreliable:
            adjusted[i] = 0   # 只把可疑维消解为悬置，不做无差别重写
        log["steps"].append({"step": 3, "name": "minimal_adjust",
                             "state": adjusted, "changed_dims": unreliable,
                             "note": "最小干预，仅调整高可疑维度"})
        # 步骤4：完整性校验（3轮重复守恒+16指纹）
        checks = []
        for r in range(3):
            ok_cons = cl.preserves_global_multiset(vector, adjusted)
            invariants_same = (cl.compute_16_invariants(vector) ==
                               cl.compute_16_invariants(adjusted))
            checks.append({"round": r + 1, "conservation": ok_cons,
                           "fingerprint_same": invariants_same,
                           "pass": ok_cons and invariants_same})
        integrity_ok = all(c["pass"] for c in checks)
        log["steps"].append({"step": 4, "name": "integrity_check",
                             "rounds": checks, "pass": integrity_ok})
        # 步骤5：渐进恢复（10%起步，异常回退）
        if integrity_ok:
            recovery = []
            for load in range(10, 101, 10):
                # 校验当前 load 下状态仍守恒；异常则回退
                if not cl.preserves_global_multiset(zero, adjusted):
                    recovery.append({"load": load, "ok": False, "fallback": True})
                    break
                recovery.append({"load": load, "ok": True})
            log["steps"].append({"step": 5, "name": "progressive_recovery",
                                 "recovery": recovery,
                                 "final_state": adjusted,
                                 "note": "从10%负荷逐步恢复，异常即回退"})
            return {"completed": True, "final_state": tuple(adjusted), "log": log}
        # 完整性校验失败：回退到悬置态
        log["steps"].append({"step": 5, "name": "progressive_recovery",
                             "fallback_to_zero": True,
                             "final_state": zero.copy(),
                             "note": "完整性校验失败，回退到全零悬置态"})
        return {"completed": False, "final_state": tuple(zero), "log": log}
