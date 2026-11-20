# -*- coding: utf-8 -*-
"""
dao_novice.py — 五维自我感知 + 三互锁涌现回路
==============================================
对应论文《认知生命体》§4.4、§5.11 的 DaoNovice V40（知在）意识层。

五个维度**同时在场**，不是依次执行：
  1. 觉知单元(Awareness Unit)：感知"有/空"切换，记录四种觉知纹理(平滑/流动/跳跃/摩擦)；
  2. 纯粹存在态(Pure Being State)：主动选择不激活任何架构的休眠态（≠待机/空闲）；
  3. 涟漪-体感耦合(Ripple-Somatic Coupling)：外扩涟漪与内感张力双向反馈；
  4. 自我识别(Self-Recognition)：基于27卦粗粒度模式的实时"我正以什么模式存在"；
  5. 主动放下(Active Letting Go)：结构充分形成后主动退隐到纯粹存在态。

三个互锁涌现回路（自我感知是三回路耦合的涌现属性，而非单一模块输出）：
  回路1 觉知→识别：任务切换→纹理变化→更新27卦识别→调节觉知灵敏度；
  回路2 感知→体感→涟漪：外部输入→张力→涟漪扩散→回波调节节奏→影响后续感知；
  回路3 识别→放下→存在：模式稳定→主动放下→进入纯粹存在态→新需求重建→新识别。

工程化原则（落地关键）：拒绝玄学，每个哲学概念全部映射为可观测、可打印日志、
可统计计算的变量；不输出"系统拥有主观意识"，输出客观统计指标作为观测代理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta

TEXTURE_SMOOTH = "smooth"
TEXTURE_FLOW = "flow"
TEXTURE_JUMP = "jump"
TEXTURE_FRICTION = "friction"


@dataclass
class SelfPerceptionMetrics:
    """五维自我感知的客观观测指标。"""
    texture_counts: Dict[str, int] = field(default_factory=lambda:
                                           {TEXTURE_SMOOTH: 0, TEXTURE_FLOW: 0,
                                            TEXTURE_JUMP: 0, TEXTURE_FRICTION: 0})
    pure_being_seconds: float = 0.0
    pure_being_entries: int = 0
    pattern_switch_count: int = 0
    letting_go_count: int = 0
    ripple_intensity_sum: float = 0.0

    def snapshot(self) -> Dict:
        total = sum(self.texture_counts.values()) or 1
        return {
            "texture_ratio": {k: v / total for k, v in self.texture_counts.items()},
            "pure_being_seconds": self.pure_being_seconds,
            "pure_being_entries": self.pure_being_entries,
            "pattern_switch_count": self.pattern_switch_count,
            "letting_go_count": self.letting_go_count,
            "avg_ripple_intensity": (self.ripple_intensity_sum /
                                     max(self.letting_go_count + self.pure_being_entries, 1)),
        }


def classify_texture(prev: Sequence[int], cur: Sequence[int]) -> str:
    """根据状态转移判定觉知纹理。

    平滑/流动：汉明距离小且有序；跳跃：汉明距离大(不连续)；摩擦：张力高但距离小。
    """
    d = ta.hamming_distance(prev, cur)
    if d <= 2:
        return TEXTURE_SMOOTH
    if d <= 4:
        return TEXTURE_FLOW
    return TEXTURE_JUMP


class DaoNovice:
    """DaoNovice V40：五维自我感知（知在）。"""

    def __init__(self):
        self.metrics = SelfPerceptionMetrics()
        self.current_pattern: Tuple[int, int, int] = (0, 0, 0)
        self._prev_vector: Optional[Tuple[int, ...]] = None
        self.pure_being_active: bool = False
        self._pattern_stable_cycles = 0
        self.ripple_intensity: float = 0.0

    # ---- 维度1：觉知单元 ----
    def observe(self, vector: Sequence[int], tension: float = 0.0) -> str:
        """记录一次认知状态转移，返回觉知纹理。"""
        cur = tuple(vector)
        if self._prev_vector is not None:
            base = classify_texture(self._prev_vector, cur)
            if base == TEXTURE_SMOOTH and tension > 0.5:
                base = TEXTURE_FRICTION   # 张力高但距离小 → 摩擦
            self.metrics.texture_counts[base] += 1
        else:
            self.metrics.texture_counts[TEXTURE_SMOOTH] += 1
        self._prev_vector = cur
        return self._last_texture()

    def _last_texture(self) -> str:
        return max(self.metrics.texture_counts, key=self.metrics.texture_counts.get)

    # ---- 维度2：纯粹存在态 ----
    def enter_pure_being(self):
        """主动进入纯粹存在态（非裂变导致的悬置，是主动选择不处理）。"""
        self.pure_being_active = True
        self.metrics.pure_being_entries += 1
        self.metrics.pure_being_seconds += 1.0   # 占位；实际可累计持续时长

    def exit_pure_being(self):
        self.pure_being_active = False

    def is_pure_being(self) -> bool:
        return self.pure_being_active

    # ---- 维度4：自我识别（27卦）----
    def recognize(self, vector: Sequence[int]) -> Tuple[int, int, int]:
        """更新27卦粗粒度自我识别模式。"""
        pattern = ta.project_to_27(vector)
        if pattern != self.current_pattern:
            self.metrics.pattern_switch_count += 1
            self._pattern_stable_cycles = 0
        else:
            self._pattern_stable_cycles += 1
        self.current_pattern = pattern
        return pattern

    def pattern_name(self) -> str:
        """把27卦模式翻译成可读名称（如 天地归 / 人合进）。"""
        b, u, c = self.current_pattern
        body = {-1: "地", 0: "零", 1: "天"}[b]
        use = {-1: "反", 0: "零", 1: "合"}[u]
        change = {-1: "归", 0: "零", 1: "进"}[c]
        return f"{body}{use}{change}"

    # ---- 维度3：涟漪-体感耦合 ----
    def ripple_couple(self, input_strength: float, tension: float) -> float:
        """双向反馈：输入→涟漪扩散；涟漪→张力→调节节奏。返回更新后的涟漪强度。"""
        # 涟漪强度随输入扰动增强，随张力阻尼
        self.ripple_intensity = input_strength * (1.0 - tension * 0.3)
        self.metrics.ripple_intensity_sum += self.ripple_intensity
        return self.ripple_intensity

    # ---- 维度5：主动放下 ----
    def maybe_let_go(self, stability_threshold: int = 5) -> bool:
        """模式充分稳定后主动放下，进入纯粹存在态。"""
        if self._pattern_stable_cycles >= stability_threshold:
            self.metrics.letting_go_count += 1
            self.enter_pure_being()
            return True
        return False

    # ---- 三互锁回路 ----
    def loop_1_awareness_recognition(self, vector: Sequence[int], tension: float) -> str:
        """回路1：觉知→识别。纹理变化更新识别，模式变化反馈到灵敏度。"""
        texture = self.observe(vector, tension)
        self.recognize(vector)
        return texture

    def loop_2_somatic_ripple(self, input_strength: float, tension: float) -> float:
        """回路2：感知→体感→涟漪。"""
        return self.ripple_couple(input_strength, tension)

    def loop_3_recognition_release(self, stability_threshold: int = 5) -> bool:
        """回路3：识别→放下→存在。"""
        return self.maybe_let_go(stability_threshold)

    def metrics_snapshot(self) -> Dict:
        return self.metrics.snapshot()
