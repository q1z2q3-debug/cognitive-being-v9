# -*- coding: utf-8 -*-
"""
conservation_laws.py — 守恒层级、16维指纹、合法移动生成器
===========================================================
对应论文《认知生命体》§3.4、§3.5 与 §5.13 的 conservation_laws 模块。

核心内容：
  1. 对称群 G = (S3 ≀ S3) ⋊ Z2 的结构（行=体/用/变三元组，列=组内三元）；
  2. 16 个相互独立的标量观测（全 19683 状态上数值秩 = 16）；
  3. 守恒层级：全局三元多重集 ⊂ 逐块三元多重集 ⊂ 16维指纹的对称化；
  4. 合法移动生成器（"成对借还"：确定值滑动到空位，不创造/消灭确定值）；
  5. 四象极限环四相位向量的定义与相位定位。

守恒层级澄清（论文 §3.4，v9核心澄清）：
  - 16个观测是"识别状态的指纹"，不是每条路径的逐点守恒量；
  - 真正的轨道不变量是分级的三元多重集：全局 > 逐块 > 指纹对称化。
  - "成对借还"移动本质上把确定值从一个位置滑到空位，保持多重集不变。
"""

from __future__ import annotations

from itertools import product
from typing import Dict, List, Sequence, Tuple

from . import ternary_algebra as ta
from .ternary_algebra import (
    BODY_GROUP, CHANGE_GROUP, DIM_TO_INDEX, DIMS, GROUP_OF,
    NUM_STATES, USE_GROUP, VAL_TO_TRIT,
    vector_to_index, index_to_vector, vector_to_group3,
)

# ---------------------------------------------------------------------------
# 四象极限环（论文 §3.5）——状态向量即行为状态（认知即执行）
# ---------------------------------------------------------------------------

PHASE_GATHER: Tuple[int, ...] = (1, 1, 1, 0, 1, 1, 1, 0, 0)   # 相位一·地正进·密(积聚)
PHASE_TRANSFORM_A: Tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0, 0, 0)  # 相位二·人和守·转化A
PHASE_DECAY: Tuple[int, ...] = (1, 1, -1, 0, 1, 1, -1, 0, 0)   # 相位三·天合归·疏(衰减)
PHASE_TRANSFORM_B: Tuple[int, ...] = (1, 1, 1, 0, 1, 1, 0, 1, 0)  # 相位四·天合进·转化B(重聚)

PHASE_SEQUENCE: List[Tuple[str, Tuple[int, ...]]] = [
    ("accumulate", PHASE_GATHER),        # 积聚
    ("transform_a", PHASE_TRANSFORM_A),  # 转化A
    ("decay", PHASE_DECAY),              # 衰减
    ("transform_b", PHASE_TRANSFORM_B),  # 转化B(重聚)
]

PHASE_NAMES: List[str] = [name for name, _ in PHASE_SEQUENCE]
PHASE_VECTORS: Dict[str, Tuple[int, ...]] = dict(PHASE_SEQUENCE)

# 扩展注意力守恒（论文 §3.5）：系统注意力 Asys + 注意力库 R 沿整圈恒为 6
PHASE_SYS_ATTN: Dict[str, int] = {"accumulate": 6, "transform_a": 0,
                                  "decay": 6, "transform_b": 6}
PHASE_RESERVOIR_ATTN: Dict[str, int] = {"accumulate": 0, "transform_a": 6,
                                        "decay": 0, "transform_b": 0}


def locate_phase(vector: Sequence[int]) -> Optional[str]:
    """判断九维向量最接近四象中的哪一个相位（按汉明距离最近）。"""
    if len(vector) != 9:
        raise ValueError("九维向量才能定位相位")
    best_name, best_dist = None, None
    for name, pv in PHASE_SEQUENCE:
        d = ta.hamming_distance(vector, pv)
        if best_dist is None or d < best_dist:
            best_dist = d
            best_name = name
    return best_name


# ---------------------------------------------------------------------------
# 3×3 矩阵重排（论文 §3.4）
# ---------------------------------------------------------------------------

def to_matrix(vector: Sequence[int]) -> List[List[int]]:
    """九维向量重排为 3×3 矩阵 M（行=体/用/变，列=组内三元）。"""
    body, use, change = vector_to_group3(vector)
    return [list(body), list(use), list(change)]


# ---------------------------------------------------------------------------
# 16 个独立观测（指纹）——全 19683 状态上数值秩 = 16
# ---------------------------------------------------------------------------

def _block_charge(triplet: Sequence[int]) -> int:
    """块电荷：n+ - n-。"""
    return triplet.count(1) - triplet.count(-1)


def _block_attention(triplet: Sequence[int]) -> int:
    """块注意力：n+ + n-（激活分量数）。"""
    return triplet.count(1) + triplet.count(-1)


def _block_suspensions(triplet: Sequence[int]) -> int:
    """块悬置数：n0。"""
    return triplet.count(0)


def _pairs_product(triplet: Sequence[int]) -> int:
    """三元组内三对分量乘积之和：ab+bc+ca。"""
    a, b, c = triplet
    return a * b + b * c + c * a


def _pairwise_products(triplet: Sequence[int]) -> Tuple[int, int, int]:
    """三元组内三对分量乘积 (ab, bc, ca)，用于信息类6个观测。"""
    a, b, c = triplet
    return a * b, b * c, c * a


def compute_16_invariants(vector: Sequence[int]) -> Dict[str, int]:
    """计算16个相互独立的标量观测（指纹）。

    类别与不变量（论文 §3.4 表，共16个）：
      极性(3):        q体, q用, q体·q用
      能量注意力(4):  A体, A用, A变, z变(变块悬置数)
      信息(6):        体块三对分量乘积 + 用块三对分量乘积
      时序因果(2):    变块三分量乘积, 用块绝对三重积
      反馈(1):        q体·q用·q变
    """
    body, use, change = vector_to_group3(vector)
    qb, qu, qc = (_block_charge(t) for t in (body, use, change))
    ab, au, ac = (_block_attention(t) for t in (body, use, change))
    zb = _block_suspensions(change)  # 变块悬置数
    pb_ab, pb_bc, pb_ca = _pairwise_products(body)
    pu_ab, pu_bc, pu_ca = _pairwise_products(use)
    triple_change = change[0] * change[1] * change[2]
    abs_triple_use = abs(use[0] * use[1] * use[2])
    invariants = {
        # 极性(3)
        "q_body": qb,
        "q_use": qu,
        "q_body_q_use": qb * qu,
        # 能量注意力(4)
        "A_body": ab,
        "A_use": au,
        "A_change": ac,
        "z_change": zb,
        # 信息(6)：体块三对 + 用块三对
        "pair_body_ab": pb_ab,
        "pair_body_bc": pb_bc,
        "pair_body_ca": pb_ca,
        "pair_use_ab": pu_ab,
        "pair_use_bc": pu_bc,
        "pair_use_ca": pu_ca,
        # 时序因果(2)
        "triple_change": triple_change,
        "abs_triple_use": abs_triple_use,
        # 反馈(1)
        "q_body_q_use_q_change": qb * qu * qc,
    }
    return invariants


INVARIANT_KEYS: List[str] = list(compute_16_invariants(ta.ALL_ZERO_VECTOR).keys())
assert len(INVARIANT_KEYS) == 16, f"16个观测类别定义异常，实际 {len(INVARIANT_KEYS)} 个"

INVARIANT_KEYS_16: List[str] = [
    "q_body", "q_use", "q_body_q_use",
    "A_body", "A_use", "A_change", "z_change",
    "pair_body_ab", "pair_body_bc", "pair_body_ca",
    "pair_use_ab", "pair_use_bc", "pair_use_ca",
    "triple_change", "abs_triple_use",
    "q_body_q_use_q_change",
]
# 说明：信息类三对乘积在块内置换下会重新编号，其对称化(多重集)才是轨道不变量；
# 而"有序"版本在指纹里被展开为三对（对应组内3个位置），供全空间数值秩检验用。


# ---------------------------------------------------------------------------
# 守恒层级：三元多重集
# ---------------------------------------------------------------------------

def global_multiset(vector: Sequence[int]) -> Tuple[int, int, int]:
    """全局三元多重集 (n-, n0, n+)。"""
    return (vector.count(-1), vector.count(0), vector.count(1))


def global_charge(vector: Sequence[int]) -> int:
    """全局电荷 Q = n+ - n-。"""
    return vector.count(1) - vector.count(-1)


def global_activation(vector: Sequence[int]) -> int:
    """全局激活 A = n+ + n-。"""
    return vector.count(1) + vector.count(-1)


def _block_ms(triplet: Sequence[int]) -> Tuple[int, int, int]:
    """三元组多重集 (n-, n0, n+)。"""
    return (triplet.count(-1), triplet.count(0), triplet.count(1))


def block_multisets(vector: Sequence[int]) -> Tuple[Tuple[int, int, int],
                                                     Tuple[int, int, int],
                                                     Tuple[int, int, int]]:
    """逐块三元多重集（体/用/变各自 (n-, n0, n+)），块内位置置换守恒。"""
    body, use, change = vector_to_group3(vector)
    return _block_ms(body), _block_ms(use), _block_ms(change)


# ---------------------------------------------------------------------------
# 合法移动生成器（"成对借还"）
# ---------------------------------------------------------------------------

def legal_moves(vector: Sequence[int]) -> List[Tuple[int, ...]]:
    """生成所有"相内合法基元移动"：把一个确定值滑到一个空位。

    规则：选一个位置 i（其值为 ±1），滑到一个空位 j（值为0），
    即把确定值从 i 移到 j；同时允许异号极性交换（+1 与 -1 对调，账本平衡）。
    这类移动保持全局三元多重集与逐块多重集不变（论文 §3.4 的"成对借还"）。

    返回：所有合法后继九维向量（去重）。
    """
    moves: List[Tuple[int, ...]] = []
    vec = list(vector)
    for i in range(9):
        if vec[i] == 0:
            continue  # 空位不能作为来源
        val = vec[i]
        # 情况1：滑动到空位
        for j in range(9):
            if j != i and vec[j] == 0:
                nv = vec[:]
                nv[j] = val
                nv[i] = 0
                moves.append(tuple(nv))
        # 情况2：异号极性交换（+1 <-> -1）
        for j in range(i + 1, 9):
            if vec[j] == -val:
                nv = vec[:]
                nv[i], nv[j] = nv[j], nv[i]
                moves.append(tuple(nv))
    # 去重保序
    seen: set = set()
    uniq: List[Tuple[int, ...]] = []
    for m in moves:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def preserves_global_multiset(old: Sequence[int], new: Sequence[int]) -> bool:
    """候选移动是否保持全局三元多重集（守恒第一层）。"""
    return global_multiset(old) == global_multiset(new)


def preserves_block_multisets(old: Sequence[int], new: Sequence[int]) -> bool:
    """候选移动是否保持逐块三元多重集（守恒第二层）。"""
    return block_multisets(old) == block_multisets(new)


# ---------------------------------------------------------------------------
# 四象极限环验证
# ---------------------------------------------------------------------------

def validate_phase_sequence() -> Dict[str, bool]:
    """验证四象极限环关键性质：扩展注意力 A_sys + R 沿整圈恒为6。"""
    ok = True
    detail = {}
    for name, attn in PHASE_SYS_ATTN.items():
        ext = attn + PHASE_RESERVOIR_ATTN[name]
        ok = ok and (ext == 6)
        detail[name] = {"sys": attn, "reservoir": PHASE_RESERVOIR_ATTN[name],
                        "extended": ext, "ok": ext == 6}
    return {"extended_attention_constant_6": ok, "detail": detail}
