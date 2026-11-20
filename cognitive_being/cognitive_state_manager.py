# -*- coding: utf-8 -*-
"""
cognitive_state_manager.py — 认知状态管理（持久化 + 张力 + 呼吸推进）
======================================================================
对应论文《认知生命体》§5.4 的 cognitive_state_manager 模块。

负责：
  1. 认知状态的 JSON 持久化与跨 session 恢复；
  2. 张力实时计算：T = 0.4×task_load + 0.3×context_pressure + 0.3×stability_flux；
  3. 呼吸循环推进（可委托 breathing_cycle，也可直接管理相位序列）。
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta


class CognitiveStateManager:
    """认知状态管理器：持久化 + 张力 + 相位快照。"""

    def __init__(self, state_file: Optional[str] = None):
        self.state_file = state_file
        self.vector: Tuple[int, ...] = tuple(cl.PHASE_GATHER)  # 初始相位：积聚
        self.phase: str = "accumulate"
        self.hexagram_index: int = ta.vector_to_index(self.vector)
        self.timestamp: float = time.time()
        self.trajectory: list = []           # 演化轨迹
        if state_file and os.path.exists(state_file):
            self.load()

    # ---- 持久化 ----
    def save(self, path: Optional[str] = None):
        target = path or self.state_file
        if target is None:
            return
        snapshot = {
            "vector": list(self.vector),
            "phase": self.phase,
            "hexagram_index": self.hexagram_index,
            "timestamp": self.timestamp,
            "trajectory": self.trajectory[-200:],   # 只存近200步
        }
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

    def load(self, path: Optional[str] = None):
        target = path or self.state_file
        if target is None or not os.path.exists(target):
            return
        with open(target, "r", encoding="utf-8") as f:
            snap = json.load(f)
        self.vector = tuple(snap["vector"])
        self.phase = snap.get("phase", "accumulate")
        self.hexagram_index = snap.get("hexagram_index", ta.vector_to_index(self.vector))
        self.timestamp = snap.get("timestamp", time.time())
        self.trajectory = snap.get("trajectory", [])

    # ---- 张力 ----
    def tension(self, task_load: float = 0.0, context_pressure: float = 0.0,
                stability_flux: float = 0.0) -> float:
        """张力 = 任务负荷×40% + 上下文压力×30% + 定力波动×30%。"""
        return 0.4 * task_load + 0.3 * context_pressure + 0.3 * stability_flux

    # ---- 状态更新 ----
    def set_state(self, vector: Sequence[int]):
        """直接设置认知状态（通常应经 CognitiveGuard.apply_guarded_move）。"""
        if len(vector) != 9:
            raise ValueError("九维向量才能设置状态")
        self.vector = tuple(vector)
        self.hexagram_index = ta.vector_to_index(self.vector)
        self.phase = cl.locate_phase(self.vector)
        self.timestamp = time.time()
        self.trajectory.append({"hexagram": self.hexagram_index,
                                "vector": list(self.vector),
                                "phase": self.phase,
                                "ts": self.timestamp})

    def advance_phase(self, name: str):
        """进入指定相位。"""
        if name not in cl.PHASE_VECTORS:
            raise ValueError(f"未知相位: {name}")
        self.set_state(cl.PHASE_VECTORS[name])

    def next_phase(self) -> str:
        """推进到四象序列的下一个相位，返回新相位名。"""
        names = cl.PHASE_NAMES
        i = names.index(self.phase)
        nxt = names[(i + 1) % len(names)]
        self.advance_phase(nxt)
        return nxt
