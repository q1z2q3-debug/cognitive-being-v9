# -*- coding: utf-8 -*-
"""Bayes悬置决策、认知守卫、混合感知测试。"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
import numpy as np

from cognitive_being import suspension_decision as sd
from cognitive_being import cognitive_guard as cg
from cognitive_being import neural_perception as np_


class TestSuspensionDecision(unittest.TestCase):
    def test_high_prob_positive(self):
        self.assertEqual(sd.bayes_optimal_action(0.95), 1)

    def test_low_prob_negative(self):
        self.assertEqual(sd.bayes_optimal_action(0.05), -1)

    def test_mid_prob_suspend(self):
        # 默认代价 λ_abstain=0.4，中间概率应悬置
        self.assertEqual(sd.bayes_optimal_action(0.5), 0)

    def test_thresholds_valid(self):
        a, b = sd.SuspensionCosts().thresholds()
        self.assertGreaterEqual(a, b)

    def test_triple_barrier(self):
        r = sd.triple_barrier_position(0, 0.5)
        self.assertEqual(r.position, 0)
        self.assertEqual(r.meta_label, "HOLD_HALF")


class TestCognitiveGuard(unittest.TestCase):
    def test_allow_sliding_move(self):
        """确定值滑到空位（源清空→目标填充，消解悬置维）应合法。"""
        guard = cg.CognitiveGuard()
        # 位置0的+1滑到位置1：全局多重集(1,8,0)保持不变
        res = guard.validate_transition((1, 0, 0, 0, 0, 0, 0, 0, 0),
                                        (0, 1, 0, 0, 0, 0, 0, 0, 0))
        self.assertTrue(res.allowed)

    def test_reject_polarity_flip(self):
        """块内异号极性交换：账本守恒却违反信息单调 → 拦截(info_monotonicity)。"""
        guard = cg.CognitiveGuard(check_block=False, check_monotonic=True)
        res = guard.validate_transition((1, -1, 0, 0, 0, 0, 0, 0, 0),
                                        (-1, 1, 0, 0, 0, 0, 0, 0, 0))
        self.assertFalse(res.allowed)
        self.assertEqual(res.violation_type, "info_monotonicity")

    def test_reject_conservation_change(self):
        guard = cg.CognitiveGuard()
        res = guard.validate_transition((1, 0, 0, 0, 0, 0, 0, 0, 0),
                                        (1, 1, 1, 1, 1, 1, 1, 1, 1))
        self.assertFalse(res.allowed)
        self.assertEqual(res.violation_type, "conservation")

    def test_apply_guarded_move_rejects_and_signal(self):
        guard = cg.CognitiveGuard(check_block=False)
        state, res = guard.apply_guarded_move((1, -1, 0, 0, 0, 0, 0, 0, 0),
                                              (-1, 1, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(state, (1, -1, 0, 0, 0, 0, 0, 0, 0))  # 原地拒绝
        self.assertEqual(res.fission_signal["type"], "cognitive_consistency")


class TestNeuralPerception(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.X = rng.normal(0, 1, (300, 3))
        self.y = np.where(self.X[:, 0] + self.X[:, 1] > 0, 1.0, 0.0)

    def test_posterior_range(self):
        f = np_.LogisticPerceptionFrontend(n_features=3)
        f.train_sgd(self.X, self.y, epochs=3)
        p = f.posterior([0.5, 0.5, 0.5])
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)

    def test_coverage_guard_ood(self):
        guard = np_.DistributionCoverageGuard()
        guard.fit(self.X)
        in_dist = guard.is_oos([0.1, 0.1, 0.1])
        out_dist = guard.is_oos([50.0, -50.0, 50.0])
        self.assertFalse(in_dist)
        self.assertTrue(out_dist)

    def test_hybrid_decision_ood_suspend(self):
        f = np_.LogisticPerceptionFrontend(n_features=3)
        f.train_sgd(self.X, self.y)
        guard = np_.DistributionCoverageGuard()
        guard.fit(self.X)
        h = np_.HybridPerception(f, guard)
        dec = h.decide([50.0, -50.0, 50.0])
        self.assertEqual(dec["action"], 0)
        self.assertTrue(dec["ood"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
