"""九维状态的距离度量。

为什么不能拿索引当距离
----------------------
index = Σ v_i · 3^i（平衡三进制的坐标值）。它的差值反映的是编码位权，
不是结构差异。上证 #186 与浦发 #19499 相差 19313（98% 的坐标空间），
但九维上只差 3 维——索引差大，结构可以很近。所以索引只当标识用。

四种度量及各自的偏差
--------------------
hamming(a,b)   逐维不同的个数。把「+1 对 −1」（翻转）和「+1 对 0」（缺失）
               同等记为 1，方向对立与证据不足不分——这是它最大的失真。
euclid(a,b)    欧式。翻转贡献 2、缺失贡献 1，能区分两者。
               华夏 vs 平安 = 2.24（一处翻转），招商 vs 平安 = 1.41（一处缺失），
               汉明却都记作 2。中段排序由它拉开。
weighted(a,b)  加权欧式，权重见 WEIGHT，按九维在判断方向上的分量分配。
flips(a,b)     只数符号相反的维数，最严的「结构对立」口径。
gaps(a,b)      返回 (翻转数, 缺失数)，供表里拆开展示。

对零态的特殊性
--------------
零向量全 0 时：hamming = 非零维数，euclid = √(非零维数)，
两者是单调变换，排序完全等价；weighted 只是在维上加权，排序也几乎不动。
所以「离零 7 层」这类说法在全 0 原点没有分辨率——它退化成「数了几个非零维」。
真要看结构，用 flips（零态下恒为 0）或非零维数本身。
"""

import math

# 权重约定（可按研究目的改写，改后需重算全部距离）：
#   正/合/归 = 2.0  趋势骨架，直接决定方向判断
#   反/守     = 1.5  反转与风险，出错代价高
#   天/地/人/进 = 1.0  外部条件与短周期动量，属于周边证据
WEIGHT = (1.0, 1.0, 1.0, 2.0, 1.5, 2.0, 2.0, 1.5, 1.0)
DIMS = ("天", "地", "人", "正", "反", "合", "归", "守", "进")


def index_of(v):
    """平衡三进制坐标。只作标识，不作距离。委托引擎实现，避免口径分叉。"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from cognitive_being.ternary_algebra import vector_to_index
    return vector_to_index(list(v))


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def euclid(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def weighted(a, b):
    return math.sqrt(sum(WEIGHT[i] * (a[i] - b[i]) ** 2 for i in range(9)))


def flips(a, b):
    return sum(1 for x, y in zip(a, b) if x and y and x != y)


def gaps(a, b):
    """返回 (翻转数, 单侧缺失数)。"""
    f = sum(1 for x, y in zip(a, b) if x and y and x != y)
    m = sum(1 for x, y in zip(a, b) if (x == 0) != (y == 0))
    return f, m


def describe(a, b):
    f, m = gaps(a, b)
    return {
        "hamming": hamming(a, b),
        "euclid": round(euclid(a, b), 3),
        "weighted": round(weighted(a, b), 3),
        "flips": f,
        "missing": m,
    }
def main():
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "out", "stock_state.json"), encoding="utf-8") as fh:
        raw = json.load(fh)
    states = {}
    for name, v in raw.items():
        last = [x for x in v["series"] if x["valid"]][-1]
        states[name] = (last["state"], last["index"])

    zero = [0] * 9
    print("== 与零态：编号越大越远，三种度量排序一致（单调变换）==")
    rows = sorted(((n, sum(1 for x in s if x), hamming(s, zero), euclid(s, zero),
                    weighted(s, zero)) for n, (s, _) in states.items()),
                  key=lambda r: (r[2], r[4]))
    for n, nz, hm, eu, wt in rows:
        print("%-18s 非零%d  汉明%2d  欧式%.2f  加权%.2f" % (n, nz, hm, eu, wt))

    print("\n== 与平安银行的距离 ==")
    ref = states["平安银行 000001.SZ"]
    print("%-18s %8s %4s %6s %7s %s" % ("标的", "索引差", "汉明", "欧式", "加权", "翻转/缺失"))
    res = []
    for n, (s, idx) in states.items():
        if n.startswith("平安银行"):
            continue
        d = describe(s, ref[0])
        res.append((n, abs(idx - ref[1]), d))
    res.sort(key=lambda r: (r[2]["hamming"], r[2]["weighted"]))
    for n, gap, d in res:
        print("%-18s %8d %4d %6.2f %7.2f   %d/%d"
              % (n, gap, d["hamming"], d["euclid"], d["weighted"], d["flips"], d["missing"]))


if __name__ == "__main__":
    main()
