# -*- coding: utf-8 -*-
"""守恒层级、16维指纹、合法移动、四象极限环测试。"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import numpy as np

from cognitive_being import ternary_algebra as ta
from cognitive_being import conservation_laws as cl


class TestInvariants(unittest.TestCase):
    def test_sixteen_invariants(self):
        self.assertEqual(len(cl.INVARIANT_KEYS), 16)

    def test_rank_16_on_full_space(self):
        """全部19683状态上16维指纹矩阵数值秩=16（论文§3.4）。"""
        X = np.array([list(cl.compute_16_invariants(ta.index_to_vector(i)).values())
                      for i in range(ta.NUM_STATES)])
        self.assertEqual(X.shape, (19683, 16))
        self.assertEqual(np.linalg.matrix_rank(X), 16)

    def test_four_phase_attention_conserved(self):
        """四象扩展注意力 A_sys + R 沿整圈恒为6（论文§3.5）。"""
        res = cl.validate_phase_sequence()
        self.assertTrue(res["extended_attention_constant_6"])


class TestPhase(unittest.TestCase):
    def test_locate_phase(self):
        self.assertEqual(cl.locate_phase(cl.PHASE_GATHER), "accumulate")
        self.assertEqual(cl.locate_phase(cl.PHASE_DECAY), "decay")
        self.assertEqual(cl.locate_phase(cl.PHASE_TRANSFORM_A), "transform_a")

    def test_legal_move_preserves_global(self):
        """合法移动保持全局三元多重集（"成对借还"）。"""
        v = (1, 0, 0, 0, 0, 0, 0, 0, -1)
        before = cl.global_multiset(v)
        for move in cl.legal_moves(v):
            self.assertEqual(cl.global_multiset(move), before)


class TestBlockMultiset(unittest.TestCase):
    def test_block_multisets(self):
        v = (1, -1, 1, 0, 0, 0, 0, 0, 0)
        b, u, c = cl.block_multisets(v)
        self.assertEqual(b, (1, 0, 2))   # 体块: -1×1, 0×0, +1×2


if __name__ == "__main__":
    unittest.main(verbosity=2)
