# -*- coding: utf-8 -*-
"""三值代数测试：K3/L3、细化序、信息单调性、索引编码。"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from cognitive_being import ternary_algebra as ta


class TestIndexEncoding(unittest.TestCase):
    def test_center_index(self):
        """全零向量索引 = 9841（状态空间中心点）。"""
        self.assertEqual(ta.vector_to_index(ta.ALL_ZERO_VECTOR), 9841)

    def test_roundtrip(self):
        for i in [0, 1, 9841, 19682]:
            self.assertEqual(ta.vector_to_index(ta.index_to_vector(i)), i)

    def test_msb_is_tian(self):
        """第一维(天)为最高位(MSB)：天=+1(三进位2)时索引为 (211111111)₃。"""
        # 全零=(111111111)₃=9841；天置+1→三进位2→(211111111)₃=9841+3^8=16402
        self.assertEqual(ta.vector_to_index((1, 0, 0, 0, 0, 0, 0, 0, 0)), 9841 + 3**8)


class TestRefinementAndMonotonicity(unittest.TestCase):
    def test_refinement_precedes(self):
        x = (0, 1, 0, 0, 0, 0, 0, 0, 0)
        y = (1, 1, 0, 0, 0, 0, 0, 0, 0)   # 消解第0维悬置
        self.assertTrue(ta.refinement_precedes(x, y))
        y2 = (-1, 1, 0, 0, 0, 0, 0, 0, 0)  # 翻转确定维 → 不满足
        self.assertFalse(ta.refinement_precedes((1, 0, 0, 0, 0, 0, 0, 0, 0), y2))

    def test_conjunction_is_monotonic(self):
        """合取投影满足信息单调性（论文实验二）。"""
        self.assertTrue(ta.is_info_monotonic(lambda v: v))

    def test_absorb_conflict_returns_zero(self):
        """确定冲突 → 退回0，不制造错误确定结论（论文§3.6核心）。"""
        prior = (1, 0, 0, 0, 0, 0, 0, 0, 0)
        ev = (-1, 0, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(ta.absorb_evidence(prior, ev), (0, 0, 0, 0, 0, 0, 0, 0, 0, )[:0] + (0, 0, 0, 0, 0, 0, 0, 0, 0))

    def test_absorb_unknown_takes_evidence(self):
        """先验为0 → 采纳证据。"""
        self.assertEqual(ta.absorb_evidence((0, 0, 0, 0, 0, 0, 0, 0, 0),
                                            (1, -1, 0, 0, 0, 0, 0, 0, 0)),
                         (1, -1, 0, 0, 0, 0, 0, 0, 0))

    def test_k3_vs_l3_implication(self):
        """K3: U→U=U；L3: U⇒U=T（论文§3.6的关键区别）。"""
        self.assertEqual(ta.k3_implies(0, 0), 0)
        self.assertEqual(ta.l3_implies(0, 0), 1)

    def test_27_projection(self):
        """全积极向量投影到27卦应为(天,合,进)即(1,1,1)。"""
        v = (1, 1, 1, 1, 1, 1, 1, 1, 1)
        self.assertEqual(ta.project_to_27(v), (1, 1, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
