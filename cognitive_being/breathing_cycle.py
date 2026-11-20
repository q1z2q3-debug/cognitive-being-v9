# -*- coding: utf-8 -*-
"""
breathing_cycle.py — 四象极限环呼吸循环（认知即执行）
=======================================================
对应论文《认知生命体》§3.5、§5.7 的 breathing_cycle 模块。

四象极限环是 19683 状态空间中的唯一吸引子，四相位循环：
  积聚 → 转化A → 衰减 → 转化B(重聚) → 积聚 …

关键（论文 §3.5 / §4.1）：这个循环**同时是认知节律和执行流程**——
  - 积聚状态本身就是信息流入；
  - 转化状态本身就是工具在执行中变化；
  - 衰减状态本身就是输出释放；
  - 重聚状态本身就是反思学习。
即"认知节律就是执行流程"，状态迁移即执行流程，无"先想再做"的翻译间隙。

v9 落地增强：把呼吸循环与真实外部世界打通——
  - 积聚相位：接收外部输入（信息流入）；
  - 转化相位：执行工具调用/内部重组；
  - 衰减相位：对外输出回答、指令；
  - 重聚相位：反思，更新内部状态轨迹。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta
from .cognitive_state_manager import CognitiveStateManager


@dataclass
class PhaseConfig:
    """各相位最小停留时间（秒）与执行钩子。"""
    min_hold: Dict[str, float] = field(default_factory=lambda: {
        "accumulate": 0.05, "transform_a": 0.05,
        "decay": 0.05, "transform_b": 0.05,
    })
    # 相位执行钩子：accumulate 收集输入 / transform 执行工具 / decay 输出 / transform_b 反思
    hook_accumulate: Optional[Callable] = None
    hook_transform: Optional[Callable] = None
    hook_decay: Optional[Callable] = None
    hook_rethink: Optional[Callable] = None


class BreathingCycle:
    """四象极限环呼吸循环：状态即行为。"""

    def __init__(self, manager: CognitiveStateManager,
                 config: Optional[PhaseConfig] = None):
        self.manager = manager
        self.config = config or PhaseConfig()
        self.step_count = 0
        self.history: List[Dict] = []

    def _current_hold(self, phase: str) -> float:
        return self.config.min_hold.get(phase, 0.0)

    def breathe_once(self, inputs: Optional[Sequence] = None) -> Dict:
        """执行一轮呼吸（一个相位周期），返回本轮的相位转移记录。

        inputs: 外部输入（仅在积聚相位被消费；None 时走"内部时钟"空转）。
        该循环的相位推进本身就是"执行流程"。
        """
        import time
        record: Dict = {}
        # 相位1：积聚（信息流入）
        if self.config.hook_accumulate:
            self.config.hook_accumulate(inputs)
        record["accumulate"] = {"state": cl.PHASE_VECTORS["accumulate"]}
        self.manager.advance_phase("accumulate")
        time.sleep(self._current_hold("accumulate"))

        # 相位2：转化A（工具在执行中变化）
        if self.config.hook_transform:
            self.config.hook_transform()
        record["transform_a"] = {"state": cl.PHASE_VECTORS["transform_a"]}
        self.manager.advance_phase("transform_a")
        time.sleep(self._current_hold("transform_a"))

        # 相位3：衰减（输出释放）
        if self.config.hook_decay:
            self.config.hook_decay()
        record["decay"] = {"state": cl.PHASE_VECTORS["decay"]}
        self.manager.advance_phase("decay")
        time.sleep(self._current_hold("decay"))

        # 相位4：转化B/重聚（反思整合）
        if self.config.hook_rethink:
            self.config.hook_rethink()
        record["transform_b"] = {"state": cl.PHASE_VECTORS["transform_b"]}
        self.manager.advance_phase("transform_b")
        time.sleep(self._current_hold("transform_b"))

        self.step_count += 1
        self.history.append({"step": self.step_count, "record": record})
        return {"step": self.step_count, "phases": record,
                "final_phase": self.manager.phase}

    def run(self, n_cycles: int = 1, inputs: Optional[Sequence] = None) -> List[Dict]:
        """连续运行 n 个呼吸周期。"""
        return [self.breathe_once(inputs) for _ in range(n_cycles)]
