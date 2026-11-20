# -*- coding: utf-8 -*-
"""
neural_perception.py — 神经感知前端 + 分布覆盖守卫（混合架构）
================================================================
对应论文《认知生命体》§3.8 与 §5.14 的 neural_perception_frontend 模块。

两层分离（论文 §3.8 的关键不对称权力）：
  - **映射层（神经感知前端）**：连续特征 x → 阳性后验 p。负责近似、学习、犯错。
    可训练、可在线更新（meta-label）、可温度校准；
  - **状态层（符号空间）**：后验 p 经 §3.7 Bayes 规则落入 {-1,0,+1}，之后一切
    在 19683 离散空间内受守恒与信息单调约束。

关键不对称权力：**神经前端无权直接输出确定结论**，它只给概率，是否承诺由符号层裁决。
因此前端再怎么学习/抖动，都不会改变符号层的守恒与逻辑规则。

分布覆盖守卫（OOD 检测）：
  - 训练数据上估计均值/协方差，Mahalanobis 距离判定新输入是否在训练分布内；
  - 阈值取训练集距离的高分位数；
  - 决策顺序：OOD ⇒ 强制悬置(0)；分布内 ⇒ p →(Bayes)→ {+1,0,-1}。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


def logistic_map(features: Sequence[float], weights: Sequence[float],
                 bias: float = 0.0) -> float:
    """逻辑映射：p = sigmoid(w·x + b)。"""
    z = bias + sum(w * x for w, x in zip(weights, features))
    return 1.0 / (1.0 + np.exp(-z))


def temperature_scale(logit: float, temperature: float = 1.0) -> float:
    """温度缩放校准：p = sigmoid(logit / T)。T>1 使分布更平滑(更保守)。"""
    return 1.0 / (1.0 + np.exp(-logit / temperature))


class LogisticPerceptionFrontend:
    """可训练的逻辑回归神经感知前端。

    把连续特征映射到阳性后验 p，提供 SGD 训练、meta-label 在线更新与温度缩放。
    前端输出的是概率，**不直接输出确定结论**。
    """

    def __init__(self, n_features: int, lr: float = 0.1,
                 temperature: float = 1.0):
        self.n_features = n_features
        self.lr = lr
        self.temperature = temperature
        rng = np.random.default_rng(0)
        self.weights = rng.normal(0, 0.1, n_features).tolist()
        self.bias = 0.0

    def posterior(self, features: Sequence[float]) -> float:
        """给出阳性后验概率（经温度缩放校准）。"""
        z = self.bias + sum(w * x for w, x in zip(self.weights, features))
        return temperature_scale(z, self.temperature)

    def train_sgd(self, X: np.ndarray, y: np.ndarray, epochs: int = 5):
        """批量 SGD 训练（最小化二元交叉熵）。"""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        for _ in range(epochs):
            for xi, yi in zip(X, y):
                p = self.posterior(xi)
                err = p - yi
                grad_w = [err * xi_k for xi_k in xi]
                grad_b = err
                self.weights = [w - self.lr * g for w, g in zip(self.weights, grad_w)]
                self.bias -= self.lr * grad_b

    def online_update(self, features: Sequence[float], meta_label: int):
        """单步在线 meta-label 更新（流数据，可抖动——论文实验五如实报告）。"""
        p = self.posterior(features)
        err = p - float(meta_label)
        self.weights = [w - self.lr * err * x for w, x in zip(self.weights, features)]
        self.bias -= self.lr * err

    def ece(self, X: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
        """期望校准误差（ECE）：预测置信度与真实频率的一致性。"""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        ps = np.array([self.posterior(x) for x in X])
        edges = np.linspace(0, 1, n_bins + 1)
        total = 0.0
        count = 0
        for i in range(n_bins):
            lo, hi = edges[i], edges[i + 1]
            mask = (ps >= lo) & (ps <= hi)
            if mask.sum() == 0:
                continue
            acc = y[mask].mean()
            conf = ps[mask].mean()
            total += mask.sum() * abs(acc - conf)
            count += mask.sum()
        return total / count if count else 0.0

    def brier(self, X: np.ndarray, y: np.ndarray) -> float:
        """Brier 分数：Σ(p-y)² / N。"""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        ps = np.array([self.posterior(x) for x in X])
        return float(np.mean((ps - y) ** 2))


class DistributionCoverageGuard:
    """分布覆盖守卫：Mahalanobis OOD 检测。

    在训练数据上估计均值与协方差（带正则化），以 Mahalanobis 距离判定新输入
    是否在训练分布内；阈值取训练集距离的高分位数（如 0.95）。
    """

    def __init__(self, quantile: float = 0.95, ridge: float = 1e-4):
        self.quantile = quantile
        self.ridge = ridge
        self.mean: Optional[np.ndarray] = None
        self.cov_inv: Optional[np.ndarray] = None
        self.threshold: Optional[float] = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.mean = X.mean(axis=0)
        cov = np.cov(X.T) + self.ridge * np.eye(X.shape[1])
        self.cov_inv = np.linalg.inv(cov)
        dists = np.array([self._mahalanobis(x) for x in X])
        self.threshold = float(np.quantile(dists, self.quantile))

    def _mahalanobis(self, x: Sequence[float]) -> float:
        if self.mean is None or self.cov_inv is None:
            raise RuntimeError("DistributionCoverageGuard 尚未 fit")
        d = np.asarray(x, dtype=float) - self.mean
        return float(np.sqrt(d @ self.cov_inv @ d))

    def is_oos(self, x: Sequence[float]) -> bool:
        """新输入是否在训练分布外（OOD）。"""
        if self.threshold is None:
            raise RuntimeError("DistributionCoverageGuard 尚未 fit")
        return self._mahalanobis(x) > self.threshold


class HybridPerception:
    """混合感知：OOD ⇒ 强制悬置；分布内 ⇒ 概率 → 符号层 Bayes 裁决。

    神经前端无权直接输出确定结论，只给出概率，是否承诺由符号层(在 loop 中)裁决。
    本类负责给出"裁决前的概率与OOD判定"，把概率交给 suspension_decision 用。
    """

    def __init__(self, frontend: LogisticPerceptionFrontend,
                 coverage_guard: DistributionCoverageGuard,
                 costs=None):
        self.frontend = frontend
        self.coverage_guard = coverage_guard
        if costs is not None:
            from . import suspension_decision as sd
            self.costs = costs if isinstance(costs, sd.SuspensionCosts) else sd.SuspensionCosts(**costs)
        else:
            from . import suspension_decision as sd
            self.costs = sd.SuspensionCosts()

    def perceive(self, features: Sequence[float]) -> Dict:
        """感知一例特征，返回 {probability, ood, forced_suspend}。"""
        ood = self.coverage_guard.is_oos(features)
        p = self.frontend.posterior(features)
        return {"probability": p, "ood": ood, "forced_suspend": ood}

    def decide(self, features: Sequence[float]):
        """完整混合裁决：OOD→强制0；分布内→Bayes三支动作。返回动作与决策信息。"""
        from . import suspension_decision as sd
        info = self.perceive(features)
        if info["forced_suspend"]:
            return {"action": 0, "region": "OOD_SUSPEND", "probability": info["probability"],
                    "ood": True}
        dec = sd.three_way_decision(info["probability"], self.costs)
        dec["ood"] = False
        return dec
