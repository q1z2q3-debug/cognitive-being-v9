# -*- coding: utf-8 -*-
"""
认知生命体（Cognitive Being）——基于三值计算基底的自感知智能体架构落地实现
==========================================================================
对应论文 v9（ReynZE & 赫曦）。本包是论文核心理论的工程化落地：

  - ternary_algebra      三值基底、K3/L3、细化序、信息单调性、19683/27卦
  - conservation_laws    守恒层级、16维指纹、合法移动、四象极限环
  - suspension_decision  Bayes最优悬置、三支决策、(α,β)、Triple Barrier
  - neural_perception    神经感知前端、分布覆盖守卫(OOD)、混合感知
  - cognitive_guard      认知守卫（守恒+信息单调双校验）
  - cognitive_encoder   关键词编码器
  - semantic_encoder    语义编码器（可插拔LLM+缓存+降级）
  - cognitive_decoder   解码器（三段输出+能力边界显式编码）
  - cognitive_state_manager 状态持久化+张力计算
  - breathing_cycle     四象极限环呼吸循环（认知即执行）
  - fission_trigger     L7裂变层（七信号+五步协议）
  - dao_novice          五维自我感知+三互锁涌现回路
  - cognitive_loop      端到端认知闭环
"""

from . import ternary_algebra
from . import conservation_laws
from . import suspension_decision
from . import neural_perception
from . import cognitive_guard
from . import cognitive_encoder
from . import semantic_encoder
from . import cognitive_decoder
from . import cognitive_state_manager
from . import breathing_cycle
from . import fission_trigger
from . import dao_novice
from . import cognitive_loop

from .cognitive_loop import CognitiveLifeform

__all__ = [
    "ternary_algebra", "conservation_laws", "suspension_decision",
    "neural_perception", "cognitive_guard", "cognitive_encoder",
    "semantic_encoder", "cognitive_decoder", "cognitive_state_manager",
    "breathing_cycle", "fission_trigger", "dao_novice", "cognitive_loop",
    "CognitiveLifeform",
]

__version__ = "0.9.0"
