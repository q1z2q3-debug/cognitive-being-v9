# -*- coding: utf-8 -*-
"""
ternary_algebra.py — 三值计算基底代数库
=========================================
对应论文《认知生命体》§3.1–§3.6 与 §5.13 的 ternary_algebra 模块。

核心内容：
  1. 三值基底 {-1, 0, +1} 上的 K3 / L3 两套连接词；
  2. 细化序 (refinement order) 偏序与信息单调性判定；
  3. 0 态吸收与冲突屏蔽算子 `absorb_evidence`（确定冲突→退回0，而非制造错误结论）；
  4. 9维三态向量的索引编码（19683 卦象空间）与 27 卦粗粒度投影。

设计原则（论文 §3.6 / §5.13）：
  - "不知道"(0) 是独立的第三态，不是中间过渡值；
  - 信息单调性：x ≼ y 且 f(x) 确定 ⇒ f(y)=f(x)，未知可随证据细化变确定，确定不得被推翻；
  - 本模块是**符号真理层**的一部分：只做确定、守恒、不凭空制造错误，不负责概率校准。
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# 常量：九维认知状态空间
# ---------------------------------------------------------------------------

# 九维固定顺序（论文 §3.2）
DIMS: List[str] = [
    "tian_conceptual",   # 天-概念
    "di_practical",      # 地-实践
    "ren_relational",    # 人-关系
    "zheng_forward",     # 正-前进
    "fan_reverse",       # 反-批判
    "he_synthesis",      # 合-综合
    "gui_return",        # 归-回归
    "shou_hold",         # 守-持守
    "jin_advance",       # 进-进取
]

# 三组：体(领域) / 用(方向) / 变(相位)
BODY_GROUP: List[str] = ["tian_conceptual", "di_practical", "ren_relational"]
USE_GROUP: List[str] = ["zheng_forward", "fan_reverse", "he_synthesis"]
CHANGE_GROUP: List[str] = ["gui_return", "shou_hold", "jin_advance"]

GROUP_OF: dict = {d: "body" for d in BODY_GROUP}
GROUP_OF.update({d: "use" for d in USE_GROUP})
GROUP_OF.update({d: "change" for d in CHANGE_GROUP})

DIM_TO_INDEX: dict = {d: i for i, d in enumerate(DIMS)}

# 三值映射：值 → 三进制位（论文 §3.2：-1→0, 0→1, +1→2）
VAL_TO_TRIT: dict = {-1: 0, 0: 1, 1: 2}
TRIT_TO_VAL: dict = {0: -1, 1: 0, 2: 1}

NUM_STATES: int = 3 ** 9  # 19683
CENTER_INDEX: int = (NUM_STATES - 1) // 2  # (111111111)₃ = 9841
ALL_ZERO_VECTOR: Tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0, 0, 0)


# ---------------------------------------------------------------------------
# 基础工具：向量 ↔ 索引
# ---------------------------------------------------------------------------

def vector_to_index(vector: Sequence[int]) -> int:
    """九维三态向量 → 19683 卦象索引。

    每维映射为三进制位（-1→0, 0→1, +1→2），第一维(天)为最高位(MSB)。
    全零向量 [0]*9 → (111111111)₃ = 9841，恰为状态空间中心点。
    """
    if len(vector) != 9:
        raise ValueError(f"认知向量必须是9维，收到 {len(vector)} 维")
    idx = 0
    for v in vector:
        if v not in (-1, 0, 1):
            raise ValueError(f"三态向量每维必须∈{{-1,0,+1}}，收到 {v}")
        idx = idx * 3 + VAL_TO_TRIT[v]
    return idx


def index_to_vector(index: int) -> Tuple[int, ...]:
    """19683 卦象索引 → 九维三态向量（天为 MSB）。"""
    if not 0 <= index < NUM_STATES:
        raise ValueError(f"卦象索引越界: {index}")
    vector = []
    for _ in range(9):
        trit = index % 3
        vector.append(TRIT_TO_VAL[trit])
        index //= 3
    return tuple(reversed(vector))


def vector_to_group3(vector: Sequence[int]) -> Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]:
    """拆分为体/用/变三个三元组。"""
    g = {d: vector[DIM_TO_INDEX[d]] for d in DIMS}
    return (tuple(g[d] for d in BODY_GROUP),
            tuple(g[d] for d in USE_GROUP),
            tuple(g[d] for d in CHANGE_GROUP))


def project_to_27(vector: Sequence[int]) -> Tuple[int, int, int]:
    """19683卦 → 27卦粗粒度模式（体/用/变各取主分量）。

    主分量取法：三值在 {-1,0,+1} 上，以"多数确定"为准；
    若组内 +1 与 -1 计数相等或全0，则该粗粒度维取 0。
    27卦模式由三个粗粒度值 (体,用,变) 各∈{-1,0,+1} 组成。
    """
    body, use, change = vector_to_group3(vector)
    def majority(triplet: Tuple[int, ...]) -> int:
        p = triplet.count(1)
        n = triplet.count(-1)
        if p > n:
            return 1
        if n > p:
            return -1
        return 0
    return majority(body), majority(use), majority(change)


def pattern_27_to_index(pattern: Sequence[int]) -> int:
    """27卦模式 → 0..26 索引（体为 MSB）。"""
    idx = 0
    for v in pattern:
        if v not in (-1, 0, 1):
            raise ValueError(f"27卦模式每维必须∈{{-1,0,+1}}，收到 {v}")
        idx = idx * 3 + VAL_TO_TRIT[v]
    return idx


def hamming_distance(a: Sequence[int], b: Sequence[int]) -> int:
    """两个九维向量之间的汉明距离（用于统合向量 / 一致性评分）。"""
    return sum(1 for x, y in zip(a, b) if x != y)


# ---------------------------------------------------------------------------
# 细化序与信息单调性
# ---------------------------------------------------------------------------

def refinement_precedes(x: Sequence[int], y: Sequence[int]) -> bool:
    """细化序 x ≼ y：每个坐标上 x_i = 0 或 x_i = y_i。

    含义：y 只能"消解" x 的悬置维，不得翻转 x 已确定的维。
    若 x ≼ y，则 y 是 x 的证据细化（信息变多但方向一致）。
    """
    if len(x) != 9 or len(y) != 9:
        raise ValueError("细化序比较需要两个9维向量")
    for xi, yi in zip(x, y):
        if xi != 0 and xi != yi:
            return False
    return True


def is_determined(vector: Sequence[int]) -> bool:
    """该九维向量是否完全确定（不含 0 态）。"""
    return all(v != 0 for v in vector)


def is_info_monotonic(f) -> bool:
    """在全部 19683 个状态上穷举判定算子 f 是否满足信息单调性。

    定义（论文 §3.6）：若 x ≼ y 且 f(x) 确定，则 f(y) = f(x)。
    返回 True 表示算子不会因获得更多证据而推翻已确定结论。
    注意：这是穷举判定，代价为 O(N²)，仅在需要时调用（测试/实验用）。
    """
    states = [index_to_vector(i) for i in range(NUM_STATES)]
    for x in states:
        fx = f(x)
        if fx is None or not is_determined(fx):
            continue
        for y in states:
            if refinement_precedes(x, y):
                if f(y) != fx:
                    return False
    return True


# ---------------------------------------------------------------------------
# 三值连接词：K3（Kleene）与 L3（Łukasiewicz）
# ---------------------------------------------------------------------------

def k3_and(a, b):
    """Kleene 强三值合取：取 min。T∧U=U, F∧U=F。"""
    return min(a, b)


def k3_or(a, b):
    """Kleene 强三值析取：取 max。"""
    return max(a, b)


def k3_not(a):
    """Kleene 否定：0 保持 0。"""
    return -a


def k3_implies(a, b):
    """Kleene 强蕴含：a→b = ¬a ∨ b。U→U = U。"""
    return max(-a, b)


def l3_implies(a, b):
    """Łukasiewicz 蕴含：U⇒U = T（与 K3 区别的关键）。"""
    if a <= b:
        return 1
    return -1


def l3_not(a):
    return -a


def l3_equiv(a, b):
    """Łukasiewicz 等价：a↔b = (a→b) ∧ (b→a)，(K3 上) = min(k3_implies(a,b), k3_implies(b,a))。"""
    return min(k3_implies(a, b), k3_implies(b, a))


# ---------------------------------------------------------------------------
# 证据吸收：0态吸收与冲突屏蔽（论文 §3.6 核心算子）
# ---------------------------------------------------------------------------

def absorb_evidence(prior: Sequence[int], evidence: Sequence[int]) -> Tuple[int, ...]:
    """逐坐标合并先验与证据，返回新状态。

    规则：
      - 先验为 0：采纳证据（0 + e → e），未知随证据细化变确定；
      - 先验确定且证据为 0：保持先验（证据无增益）；
      - 先验确定且证据同向：保持；
      - **先验确定且证据反向：确定冲突 → 退回 0（悬置），而不是制造一个错误的确定结论。**

    该算子满足信息单调性（证据吸收不推翻已确定结论，只可能引入悬置）。
    """
    if len(prior) != 9 or len(evidence) != 9:
        raise ValueError("先验与证据都必须是9维向量")
    out = []
    for p, e in zip(prior, evidence):
        if p == 0:
            out.append(e)          # 未知 → 采纳证据
        elif e == 0 or e == p:
            out.append(p)          # 保持确定
        else:
            out.append(0)          # 确定冲突 → 悬置
    return tuple(out)


# ---------------------------------------------------------------------------
# 三值逻辑门：合取/析取投影（论文 §3.6 / 实验二用）
# ---------------------------------------------------------------------------

def conjunctive_project(x: Sequence[int], y: Sequence[int]) -> Tuple[int, ...]:
    """逐坐标合取投影（K3 合取）。满足信息单调性。"""
    return tuple(k3_and(a, b) for a, b in zip(x, y))


def disjunctive_project(x: Sequence[int], y: Sequence[int]) -> Tuple[int, ...]:
    """逐坐标析取投影（K3 析取）。满足信息单调性。"""
    return tuple(k3_or(a, b) for a, b in zip(x, y))


def majority_vote(x: Sequence[int], y: Sequence[int], z: Sequence[int]) -> Tuple[int, ...]:
    """逐坐标多数表决（三选二）。论文实验二证明其**不满足**信息单调性。"""
    out = []
    for a, b, c in zip(x, y, z):
        s = (1 if a == 1 else 0) + (1 if b == 1 else 0) + (1 if c == 1 else 0)
        n = (1 if a == -1 else 0) + (1 if b == -1 else 0) + (1 if c == -1 else 0)
        if s > n:
            out.append(1)
        elif n > s:
            out.append(-1)
        else:
            out.append(0)
    return tuple(out)


def vector_tostring(vector: Sequence[int]) -> str:
    """九维向量 → 紧凑字符串表示（如 [+1,+1,+1,0,+1,+1,+1,0,0]）。"""
    return "[" + ",".join(str(v) for v in vector) + "]"
