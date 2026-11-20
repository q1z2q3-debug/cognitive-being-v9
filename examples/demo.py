# -*- coding: utf-8 -*-
"""
demo.py — 认知生命体端到端演示
================================
展示完整闭环：文本输入 → 感知(语义/关键词) → 符号层Bayes三支决策 →
吸收证据 → 认知守卫双校验 → 四象呼吸循环 → 解码器受约束提示 → 五维自我感知。

运行：python3 examples/demo.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cognitive_being.cognitive_loop import CognitiveLifeform
from cognitive_being import semantic_encoder as se
from cognitive_being import suspension_decision as sd


def banner(t):
    print("\n" + "=" * 66)
    print("  " + t)
    print("=" * 66)


def main():
    banner("认知生命体端到端演示 (v0.9 落地)")
    print("论文: 《认知生命体：基于三值计算基底的自感知智能体架构》v9")
    print("三层分离: 连续感知 →(Bayes三支决策)→ 离散19683状态 →(守恒+信息单调守卫)→ 呼吸/解码/自我感知")

    # 接入一个"LLM语义编码器"（此处用默认桩演示接口；真实可替换为大模型 callable）
    life = CognitiveLifeform(
        llm=se.default_llm_stub,
        costs=sd.SuspensionCosts(lambda_fp=1.0, lambda_fn=1.0, lambda_abstain=0.4),
    )

    inputs = [
        ("推进", "我们积极推进概念创新、理论整合，开拓进取，回归本质", 0.3, 0.3, 0.1),
        ("批判", "这个方案需要严格质疑、批判审视，验证其基础假设是否成立", 0.6, 0.5, 0.4),
        ("冲突检验", "既要全力推进落地执行，又要全面质疑推翻它", 0.8, 0.7, 0.6),
        ("平静", "休息一下，什么也不做，静静存在", 0.05, 0.05, 0.05),
    ]

    for tag, text, tl, cp, sf in inputs:
        banner(f"[{tag}] 输入: “{text}”")
        r = life.process(text, task_load=tl, context_pressure=cp, stability_flux=sf)
        print(f"  感知向量     : {list(r['perceived_vector'])}")
        print(f"  吸收证据     : {list(r['absorbed_vector'])}")
        print(f"  最终状态     : {list(r['final_state'])}")
        print(f"  卦象 / 相位  : #{r['hexagram']} / {r['phase']}")
        print(f"  张力         : {r['tension']:.2f}")
        print(f"  觉知纹理     : {r['texture']}")
        print(f"  自我识别(27卦): {r['pattern']}")
        print(f"  裂变触发     : {r['fission_triggered']}")
        if r['fission_triggered']:
            print(f"  !! L7 裂变已触发，见 fission_log ({len(life.fission_log)} 次)")
        print(f"  —— 解码器注入(节选) ——")
        print(r['prompt'])

    banner("五维自我感知观测指标 (客观代理)")
    for k, v in life.dao.metrics_snapshot().items():
        print(f"  {k}: {v}")

    banner("演化轨迹 (状态即行为，跨轮持久)")
    print(f"  共 {len(life.manager.trajectory)} 步认知演化")
    for tr in life.manager.trajectory[-4:]:
        print(f"    #{tr['hexagram']:>5} 相位={tr['phase']:<11} 向量={list(tr['vector'])}")


if __name__ == "__main__":
    main()
