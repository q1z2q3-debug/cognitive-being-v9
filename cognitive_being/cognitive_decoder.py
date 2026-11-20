# -*- coding: utf-8 -*-
"""
cognitive_decoder.py — 认知解码器（状态 → LLM 提示词注入）
=============================================================
对应论文《认知生命体》§5.3 的 cognitive_decoder 模块。

编码器的逆过程——将认知状态向量转换为 LLM 可理解的提示词注入。
采用三段输出（借鉴 gelab-zero 能力边界编码思想）：
  1. 认知状态描述；
  2. 能力边界声明（显式标记哪些维度处于0态-不确定 / -1态-受限）；
  3. 行为倾向指引。

关键设计（论文 §5.3）：解码器显式注入哪些维度处于0态(不确定)或-1态(受限)，
使 LLM 输出受认知状态约束，而非脱离认知状态自由生成。
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta
from .ternary_algebra import DIMS

DIM_LABELS = {
    "tian_conceptual": "天-概念",
    "di_practical": "地-实践",
    "ren_relational": "人-关系",
    "zheng_forward": "正-前进",
    "fan_reverse": "反-批判",
    "he_synthesis": "合-综合",
    "gui_return": "归-回归",
    "shou_hold": "守-持守",
    "jin_advance": "进-进取",
}

PHASE_SEMANTICS = {
    "accumulate": "积聚：信息流入、主动收集",
    "transform_a": "转化：内部重组、工具在执行中变化",
    "decay": "衰减：认知向外释放、输出结果",
    "transform_b": "重聚：反思整合、为下一轮准备",
}


class CognitiveDecoder:
    """认知状态 → 三段提示词。"""

    def decode(self, vector: Sequence[int],
               hexagram_index: int = None,
               phase: str = None) -> Dict[str, str]:
        """解码认知状态为三段提示词，返回 dict(描述/边界/指引) 与拼接 prompt。"""
        if len(vector) != 9:
            raise ValueError("解码器需要9维三态向量")
        if hexagram_index is None:
            hexagram_index = ta.vector_to_index(vector)
        if phase is None:
            phase = cl.locate_phase(vector)

        # ---- 段1：认知状态描述 ----
        desc_parts = [f"卦象#{hexagram_index}（{ta.vector_tostring(vector)}）"]
        desc_parts.append(f"当前相位：{phase} — {PHASE_SEMANTICS.get(phase, '未知')}")
        active = [DIM_LABELS[d] for d, v in zip(DIMS, vector) if v == 1]
        neg = [DIM_LABELS[d] for d, v in zip(DIMS, vector) if v == -1]
        if active:
            desc_parts.append(f"活跃维度：{'、'.join(active)}")
        if neg:
            desc_parts.append(f"受限维度：{'、'.join(neg)}")
        description = "\n".join(desc_parts)

        # ---- 段2：能力边界声明（0态不确定 / -1态受限）----
        uncertain = [DIM_LABELS[d] for d, v in zip(DIMS, vector) if v == 0]
        restricted = [DIM_LABELS[d] for d, v in zip(DIMS, vector) if v == -1]
        boundary_lines = ["【能力边界声明】"]
        if uncertain:
            boundary_lines.append("当前处于不确定态(0)的维度：" + "、".join(uncertain))
            boundary_lines.append("这些维度上的断言应明确标注为不确定，禁止假装确定。")
        else:
            boundary_lines.append("无不确定维度。")
        if restricted:
            boundary_lines.append("当前处于受限态(-1)的维度：" + "、".join(restricted))
            boundary_lines.append("这些维度上应保持克制/批判，不宜贸然推进。")
        boundary = "\n".join(boundary_lines)

        # ---- 段3：行为倾向指引 ----
        guidance_lines = ["【行为倾向指引】"]
        guidance_lines.append(f"请围绕「{phase}」相位语义组织当前行为：{PHASE_SEMANTICS.get(phase, '')}。")
        guidance_lines.append("输出必须遵守上述能力边界：不确定维度不得假装确定，受限维度不得强行推进。")
        guidance = "\n".join(guidance_lines)

        prompt = "\n\n".join([description, boundary, guidance])
        return {"description": description, "boundary": boundary,
                "guidance": guidance, "prompt": prompt}
