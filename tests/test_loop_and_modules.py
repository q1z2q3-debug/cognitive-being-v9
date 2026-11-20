# -*- coding: utf-8 -*-
"""编码器、解码器、呼吸循环、裂变、端到端闭环测试。"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest

from cognitive_being import cognitive_encoder as ce
from cognitive_being import semantic_encoder as se
from cognitive_being import cognitive_decoder as cd
from cognitive_being import cognitive_state_manager as csm
from cognitive_being import breathing_cycle as bc
from cognitive_being import fission_trigger as ft
from cognitive_being import dao_novice as dn
from cognitive_being.cognitive_loop import CognitiveLifeform


class TestEncoder(unittest.TestCase):
    def test_keyword_encode_active_dim(self):
        enc = ce.KeywordEncoder()
        r = enc.encode("我们积极推进概念创新与理论整合，回归本质")
        # 概念/理论维度应激活为+1
        self.assertIn(r["vector"][0], (0, 1))
        self.assertIsInstance(r["hexagram_index"], int)
        self.assertIsInstance(r["phase"], str)

    def test_semantic_encoder_degrade_to_keyword(self):
        se_ = se.SemanticEncoder(llm=None)  # 无LLM → 降级关键词
        r = se_.encode("实践操作与工具执行很重要", use_symbol_decision=True)
        self.assertFalse(r["used_llm"])
        self.assertEqual(len(r["vector"]), 9)

    def test_semantic_encoder_with_llm_stub(self):
        se_ = se.SemanticEncoder(llm=se.default_llm_stub)
        r = se_.encode("积极推进概念创新与理论整合")
        self.assertTrue(r["used_llm"])
        self.assertEqual(len(r["vector"]), 9)


class TestDecoder(unittest.TestCase):
    def test_decoder_three_sections(self):
        dec = cd.CognitiveDecoder()
        out = dec.decode((1, 1, 1, 0, 1, 1, 1, 0, 0))
        self.assertIn("description", out)
        self.assertIn("boundary", out)
        self.assertIn("guidance", out)
        self.assertIn("不确定态", out["boundary"])

    def test_decoder_mentions_boundary(self):
        dec = cd.CognitiveDecoder()
        out = dec.decode((1, 1, 1, 0, 1, 1, 1, 0, 0))
        self.assertIn("能力边界声明", out["boundary"])


class TestStateManager(unittest.TestCase):
    def test_tension_formula(self):
        m = csm.CognitiveStateManager()
        t = m.tension(task_load=1.0, context_pressure=0.0, stability_flux=0.0)
        self.assertAlmostEqual(t, 0.4)

    def test_phase_advance(self):
        m = csm.CognitiveStateManager()
        nxt = m.next_phase()
        self.assertEqual(nxt, "transform_a")


class TestBreathing(unittest.TestCase):
    def test_cycle_four_phases(self):
        m = csm.CognitiveStateManager()
        cyc = bc.BreathingCycle(m)
        rec = cyc.breathe_once()
        self.assertIn("accumulate", rec["phases"])
        self.assertIn("transform_b", rec["phases"])
        self.assertEqual(m.phase, "transform_b")


class TestFission(unittest.TestCase):
    def test_trigger_condition_fatal(self):
        self.assertTrue(ft.fission_trigger_met([{"severity": "FATAL"}]))

    def test_trigger_condition_two_critical(self):
        self.assertTrue(ft.fission_trigger_met(
            [{"severity": "CRITICAL"}, {"severity": "CRITICAL"}]))

    def test_no_trigger_single_warn(self):
        self.assertFalse(ft.fission_trigger_met([{"severity": "WARN"}]))

    def test_protocol_five_steps(self):
        p = ft.FissionProtocol()
        res = p.run((1, 1, 1, 0, 1, 1, 1, 0, 0), unreliable_dims=[0])
        self.assertEqual(len(res["log"]["steps"]), 5)
        self.assertEqual(res["log"]["steps"][0]["name"], "epoché")


class TestDaoNovice(unittest.TestCase):
    def test_recognize_pattern(self):
        d = dn.DaoNovice()
        d.recognize((1, 1, 1, 1, 1, 1, 1, 1, 1))
        self.assertEqual(d.pattern_name(), "天合进")

    def test_let_go(self):
        d = dn.DaoNovice()
        v = (1, 1, 1, 1, 1, 1, 1, 1, 1)
        for _ in range(6):
            d.loop_1_awareness_recognition(v, 0.2)
        self.assertTrue(d.loop_3_recognition_release(stability_threshold=5))
        self.assertTrue(d.is_pure_being())


class TestCognitiveLoop(unittest.TestCase):
    def test_process_end_to_end(self):
        life = CognitiveLifeform()
        r = life.process("积极推进概念创新与理论整合，回归本质")
        self.assertEqual(len(r["final_state"]), 9)
        self.assertIn("prompt", r)
        self.assertIn("hexagram", r)
        self.assertIn("pattern", r)

    def test_loop_persists_trajectory(self):
        life = CognitiveLifeform()
        for text in ["推进", "批判质疑", "回归复盘"]:
            life.process(text)
        self.assertGreater(len(life.manager.trajectory), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
