# -*- coding: utf-8 -*-
"""
semantic_encoder.py — 语义编码器（可插拔 LLM）
=================================================
对应论文《认知生命体》§5.5 的 semantic_encoder 模块。

增强版编码器，提供可插拔的 LLM 接口替代关键词匹配：
  - 接口签名：callable(text: str) -> {"dim_scores": {...}, "confidence": float}
  - 不硬编码任何 API 端点，LLM callable 作为参数传入；
  - MD5 哈希缓存：相同输入直接返回缓存结果，减少 LLM 调用；
  - 自动降级：LLM 不可用时自动降级到关键词匹配编码器。

关键（论文 §5.5 / §3.8）：LLM 语义编码器输出的是**各维度后验概率/得分**，
不是直接输出确定的三态向量——把最终三值裁决权交给符号层（suspension_decision），
维持神经-符号分离。
"""

from __future__ import annotations

import hashlib
import json
from typing import Callable, Dict, Optional

from . import ternary_algebra as ta
from . import conservation_laws as cl
from . import suspension_decision as sd
from .cognitive_encoder import KeywordEncoder
from .ternary_algebra import DIMS

# LLM callable 类型：text -> {"dim_scores": {dim: 0..1 概率或 -1..1 得分}, "confidence": float}
LLMCallable = Callable[[str], Dict]


class SemanticEncoder:
    """语义编码器：可插拔 LLM + 缓存 + 自动降级。"""

    def __init__(self, llm: Optional[LLMCallable] = None,
                 keyword_fallback: Optional[KeywordEncoder] = None,
                 costs: Optional[sd.SuspensionCosts] = None,
                 use_cache: bool = True):
        self.llm = llm
        self.keyword = keyword_fallback or KeywordEncoder()
        self.costs = costs or sd.SuspensionCosts()
        self.use_cache = use_cache
        self._cache: Dict[str, Dict] = {}

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _llm_dim_posteriors(self, text: str) -> Optional[Dict[str, float]]:
        """调用 LLM 得到各维度后验概率（若可用）。失败/异常返回 None。"""
        if self.llm is None:
            return None
        try:
            out = self.llm(text)
            dim_scores = out.get("dim_scores")
            if not isinstance(dim_scores, dict):
                return None
            # 只取九维
            return {d: float(dim_scores.get(d, 0.0)) for d in DIMS}
        except Exception:
            return None

    def encode(self, text: str, use_symbol_decision: bool = True) -> Dict[str, object]:
        """编码一例文本。

        use_symbol_decision=True 时：LLM 后验概率 → Bayes 三支决策 → 三态向量
        （符号层裁决，保持神经-符号分离）。
        use_symbol_decision=False 时：退化为关键词编码器直接出三态向量（降级路径）。
        """
        cache_key = self._cache_key(text)
        if self.use_cache and cache_key in self._cache:
            return dict(self._cache[cache_key])

        llm_p = self._llm_dim_posteriors(text)
        if llm_p is not None and use_symbol_decision:
            vector = []
            for d in DIMS:
                action = sd.bayes_optimal_action(llm_p[d], self.costs)
                vector.append(action)
            vector_t = tuple(vector)
            used_llm = True
        else:
            enc = self.keyword.encode(text)
            vector_t = enc["vector"]
            used_llm = False

        result = {
            "vector": vector_t,
            "hexagram_index": ta.vector_to_index(vector_t),
            "phase": cl.locate_phase(vector_t),
            "used_llm": used_llm,
            "llm_posteriors": llm_p,
        }
        if self.use_cache:
            self._cache[cache_key] = result
        return result


def default_llm_stub(text: str) -> Dict:
    """默认 LLM 桩：演示用。把关键词编码器的原始得分映射为后验概率。

    真实接入时，用实际大模型 callable 替换即可（接口见 LLMCallable）。
    """
    enc = KeywordEncoder()
    raw = enc.dimension_scores(text)
    # 把 [-1,1] 得分映射为 [0,1] 概率：p = (s+1)/2
    dim_scores = {d: (raw[d] + 1) / 2 for d in DIMS}
    return {"dim_scores": dim_scores, "confidence": 0.8}
