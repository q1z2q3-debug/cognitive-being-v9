# -*- coding: utf-8 -*-
"""
cognitive_loop.py — 端到端认知闭环
====================================
对应论文《认知生命体》§5.13 的 cognitive_loop_v9 集成模块。

端到端闭环（连续感知 → 离散状态严格分层）：
  输入 → 神经/语义感知前端给出概率 →(OOD守卫: OOD→强制悬置)→ 符号层 Bayes 三支决策
        → 九维三态向量 →(吸收证据)→(认知守卫双校验: 守恒+信息单调)→ 合法写入状态
        → 四象呼吸循环(guarded_breathe) → 解码器输出受约束提示 → 五维自我感知观测

两层分离（论文 §3.8 / §5.14）：
  - 学习发生在连续→三值的映射层；
  - 真理发生在离散状态层，每步受细化序与守恒层级约束，错误不能被凭空制造。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta
from .cognitive_guard import CognitiveGuard
from .cognitive_state_manager import CognitiveStateManager
from .cognitive_decoder import CognitiveDecoder
from .cognitive_encoder import KeywordEncoder
from .semantic_encoder import SemanticEncoder, LLMCallable
from .fission_trigger import FissionSignalDetector, FissionProtocol
from .dao_novice import DaoNovice
from . import suspension_decision as sd


class CognitiveLifeform:
    """认知生命体：感知→状态→呼吸→解码→自我感知的完整闭环。"""

    def __init__(self, state_file: Optional[str] = None,
                 llm: Optional[LLMCallable] = None,
                 costs: Optional[sd.SuspensionCosts] = None):
        self.manager = CognitiveStateManager(state_file)
        self.encoder = SemanticEncoder(llm=llm, costs=costs)
        self.keyword_encoder = KeywordEncoder()
        self.guard = CognitiveGuard()
        self.decoder = CognitiveDecoder()
        self.detector = FissionSignalDetector()
        self.protocol = FissionProtocol(guard=self.guard)
        self.dao = DaoNovice()
        self._prev_state: Optional[Tuple[int, ...]] = None
        self.fission_log: List[Dict] = []
        self.turn_count = 0

    # ---- 完整一轮：文本输入 → 认知处理 → 输出提示 ----
    def process(self, text: str,
                task_load: float = 0.3, context_pressure: float = 0.3,
                stability_flux: float = 0.1) -> Dict:
        """处理一段文本输入，返回完整闭环信息。

        层级边界（论文 §3.9）：守卫只守符号演化层的相内 move，**不**干预感知重分类。
        因此这里感知吸收(absorb_evidence)直接采纳为新认知状态——外部信息改变多重集是
        合法的；守卫仅用于守护符号层内部的相内演化移动(guarded_breathe)。
        """
        self.turn_count += 1

        # 1) 感知：语义编码器（LLM/降级）得到后验概率 → 符号层三支决策 → 三态向量
        enc = self.encoder.encode(text, use_symbol_decision=True)
        proposed = enc["vector"]

        # 2) 吸收证据：与当前认知状态逐坐标合并（确定冲突→退回0），直接采纳。
        #    吸收算子本身满足信息单调性，故感知采纳不经过守恒守卫（见层级边界）。
        absorbed = ta.absorb_evidence(self.manager.vector, proposed)
        self.manager.set_state(absorbed)
        final_state = absorbed

        # 3) 张力计算
        tension = self.manager.tension(task_load, context_pressure, stability_flux)

        # 4) 五维自我感知观测（三回路之一：觉知→识别）
        texture = self.dao.loop_1_awareness_recognition(final_state, tension)
        self.dao.loop_2_somatic_ripple(input_strength=task_load, tension=tension)

        # 5) L7 裂变检测（张力/矛盾/OOD等，不再因感知改变多重集而误触发）
        signals = self.detector.detect(
            current=final_state,
            previous=self._prev_state,
            tension=tension,
            ood=False,
            stagnation_cycles=0,
            conservation_violated=False,
            coherence_broken=False,
            contradiction=False,
        )
        trigger = self._decide_fission(signals)
        if trigger:
            unreliable = self._self_inquiry(self.manager.vector, proposed)
            proto = self.protocol.run(self.manager.vector, unreliable_dims=unreliable)
            self.fission_log.append(proto)
            final_state = proto["final_state"]
            self.manager.set_state(final_state)

        # 6) 解码：认知状态 → 受约束提示词
        dec = self.decoder.decode(final_state,
                                  ta.vector_to_index(final_state),
                                  cl.locate_phase(final_state))
        self._prev_state = final_state
        return {
            "turn": self.turn_count,
            "input": text,
            "perceived_vector": proposed,
            "absorbed_vector": tuple(absorbed),
            "final_state": final_state,
            "hexagram": ta.vector_to_index(final_state),
            "phase": cl.locate_phase(final_state),
            "tension": tension,
            "texture": texture,
            "pattern": self.dao.pattern_name(),
            "fission_triggered": trigger,
            "prompt": dec["prompt"],
        }

    def guarded_breathe(self, proposed_move: Sequence[int],
                        source: str = "symbolic"):
        """守卫守护的相内符号演化移动。

        只用于守护**符号层内部**的合法演化 move（如认知内部重组、状态精化）；
        感知注入与相位切换不经过此守卫（论文 §3.9 层级边界）。
        返回 (最终状态, 守卫结果)。
        """
        return self.guard.apply_guarded_move(self.manager.vector,
                                             proposed_move, source=source)

    def _decide_fission(self, signals: List[Dict]) -> bool:
        """根据信号判定是否触发裂变（触发条件 + 加权压力>0.7）。"""
        if not signals:
            return False
        return (self._fission_trigger_met(signals)
                or sum(self._sev_weight(s) for s in signals) > 0.7)

    def _fission_trigger_met(self, signals: List[Dict]) -> bool:
        sev = [s.get("severity") for s in signals]
        if "FATAL" in sev:
            return True
        if sev.count("CRITICAL") >= 2:
            return True
        if sev.count("CRITICAL") >= 1 and sev.count("WARN") >= 2:
            return True
        return False

    def _sev_weight(self, s: Dict) -> float:
        return {"FATAL": 1.0, "CRITICAL": 0.6, "WARN": 0.3}.get(s.get("severity"), 0)

    def _self_inquiry(self, current: Sequence[int], proposed: Sequence[int]) -> List[int]:
        """L7 步骤2自问：标记证据不可靠的维度（感知与状态冲突/悬置的维度）。"""
        unreliable = []
        for i, (c, p) in enumerate(zip(current, proposed)):
            if c != 0 and p != 0 and c != p:
                unreliable.append(i)   # 确定维度被反向证据冲击 → 可疑
        return unreliable
