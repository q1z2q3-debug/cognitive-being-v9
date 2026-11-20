# -*- coding: utf-8 -*-
"""
cognitive_encoder.py — 认知编码器（文本 → 九维三态向量）
===========================================================
对应论文《认知生命体》§5.2 的 cognitive_encoder 模块。

将自然语言文本转换为九维三态向量，进而定位到 19683 卦象状态与四象相位。
关键词匹配 + 加权归一化 + 阈值判定（threshold 默认 0.3，可配置），纯标准库实现。

编码流程（论文 §5.2 伪代码）：
  scores[dim] = (pos_score - neg_score) / max(pos_score, neg_score, 1)
  |scores| < threshold ⇒ 0（不确定/悬置）
  scores > 0 ⇒ +1；scores < 0 ⇒ -1
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from . import conservation_laws as cl
from . import ternary_algebra as ta
from .ternary_algebra import DIMS

# 每维关键词表：{正向, 反向}。中英混合，供关键词编码器使用。
KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "tian_conceptual": {
        "pos": ["概念", "抽象", "理论", "思想", "逻辑", "本质", "concept", "theory",
                "abstract", "logic", "principle", "思辨", "理念"],
        "neg": ["具体", "实务", "操作", "执行", "细节", "concrete", "practical",
                "operational", "implementation", "手感", "落地"],
    },
    "di_practical": {
        "pos": ["实践", "操作", "工具", "执行", "落地", "实现", "动手", "practical",
                "operate", "tool", "implement", "execute", "手工", "实测"],
        "neg": ["空想", "理论", "纸上谈兵", "抽象", "只说不做", "theoretical",
                "speculative", "talk", "空谈", "设想"],
    },
    "ren_relational": {
        "pos": ["关系", "协作", "社交", "合作", "团队", "沟通", "协调", "人脉",
                "social", "collaboration", "cooperate", "team", "relation",
                "人际", "共情", "同理"],
        "neg": ["独处", "孤立", "对抗", "冲突", "alone", "isolate", "conflict",
                "solo", "敌对", "隔阂", "封闭"],
    },
    "zheng_forward": {
        "pos": ["前进", "推进", "拓展", "进取", "积极", "主动", "乐观", "增长",
                "forward", "advance", "proactive", "positive", "growth", "扩展"],
        "neg": ["后退", "保守", "收缩", "悲观", "消极", "退缩", "backward",
                "retreat", "passive", "pessimistic", "防御", "退却"],
    },
    "fan_reverse": {
        "pos": ["质疑", "批判", "反思", "挑战", "审视", "怀疑", "验证", "推翻",
                "criticize", "question", "reflect", "challenge", "skeptic",
                "质疑权威", "证伪"],
        "neg": ["盲从", "接受", "顺从", "照搬", "follow", "accept", "obey",
                "迷信", "轻信", "无条件"],
    },
    "he_synthesis": {
        "pos": ["综合", "整合", "调和", "平衡", "统一", "融合", "权衡", "synthesize",
                "integrate", "balance", "unify", "harmonize", "协调综合", "统筹"],
        "neg": ["割裂", "对立", "片面", "极端", "分裂", "split", "confront",
                "one-sided", "极端化", "失衡"],
    },
    "gui_return": {
        "pos": ["回归", "回顾", "复盘", "整理", "沉淀", "归零", "retrospect",
                "return", "review", "settle", "back_to_root", "复盘总结", "整理"],
        "neg": ["向前冲", "冒进", "忽略历史", "no_review", "忘本", "急进",
                "不回顾", "甩开"],
    },
    "shou_hold": {
        "pos": ["保持", "稳定", "守成", "维持", "坚守", "现状", "hold", "stable",
                "steady", "maintain", "defend", "守", "稳住"],
        "neg": ["改变", "突破", "激进", "变革", "不稳", "change", "break",
                "aggressive", "颠覆", "冒险"],
    },
    "jin_advance": {
        "pos": ["突破", "创新", "进取", "开拓", "前进", "创新突破", "breakthrough",
                "innovate", "advance", "pioneer", "开拓进取", "探索新"],
        "neg": ["守旧", "停滞", "固守", "不求变", "stale", "stagnant",
                "conservative", "原地踏步", "墨守成规"],
    },
}


class KeywordEncoder:
    """关键词编码器：文本 → 九维三态向量 → 卦象 → 四象相位。"""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold

    def dimension_scores(self, text: str) -> Dict[str, float]:
        """计算九维各自的正向/反向关键词得分差（归一化到[-1,1]）。"""
        text_l = text.lower()
        scores: Dict[str, float] = {}
        for dim in DIMS:
            pos_kw = KEYWORDS[dim]["pos"]
            neg_kw = KEYWORDS[dim]["neg"]
            pos_score = sum(1 for kw in pos_kw if kw.lower() in text_l)
            neg_score = sum(1 for kw in neg_kw if kw.lower() in text_l)
            denom = max(pos_score, neg_score, 1)
            scores[dim] = (pos_score - neg_score) / denom
        return scores

    def encode(self, text: str) -> Dict[str, object]:
        """编码一例文本。返回 {vector, hexagram_index, phase, raw_scores}。"""
        raw = self.dimension_scores(text)
        vector = []
        for dim in DIMS:
            s = raw[dim]
            if abs(s) < self.threshold:
                vector.append(0)
            elif s > 0:
                vector.append(1)
            else:
                vector.append(-1)
        vector_t = tuple(vector)
        idx = ta.vector_to_index(vector_t)
        phase = cl.locate_phase(vector_t)
        return {"vector": vector_t, "hexagram_index": idx, "phase": phase,
                "raw_scores": raw}
