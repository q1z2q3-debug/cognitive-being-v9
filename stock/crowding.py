"""拥挤度：把「同构」从形容词变成三个可复算的数。

背景
----
L1 只回答「哪个行业值得看」，L2 只回答「行业内哪只值得看」。
这两层都有一个没被度量的前提：**样本之间是不是彼此独立**。
如果十只股票其实是同一个形态，那 L1 的行业得分、L2 的个股排序都建立在
重复样本之上——名义上 124 只，实际可下注的独立想法可能只有几个。
本模块只算这件事，不下买卖结论。

三个指标
--------
1. 行业内区分度 `dup`：1 - 不同索引数 / 行业内样本数。
   接近 0 说明行业内个股形态分化，L2 的组内比较是有信息量的；
   接近 1 说明这个行业的个股塌成一团，组内排序等于抓阄。

2. 索引跨行业跨度 `reach`：一个九维索引覆盖了多少个申万一级行业。
   九维算的是价格形态，不认行业标签。reach 高的索引是「公共形态」，
   它出现在哪个行业都不构成行业超额信息；reach=1 的索引才是这个行业独有的。

3. 候选池独立信号数 `independent`：按汉明距离 <= eps 做并查集聚类，
   名义 N 只会压成 K 组。K/N 就是这轮真正可分散的独立想法比例。
   这一项是 L4 去重的事前度量——L4 做事后删除，这里提前报出代价。

口径
----
全部读 out/stock_state.json 最后一个有效交易日，窗口与其他模块一致（26 根）。
不做任何基本面、资金流推断；缺口不补。
"""

import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))

from stock.metrics import hamming                      # noqa: E402
from stock.universe import UNIVERSE, INDEX             # noqa: E402

try:
    from ternary_algebra import index_to_vector, vector_tostring
except ImportError:                                     # 包内路径
    from cognitive_being.ternary_algebra import index_to_vector, vector_tostring

# 阈值：reach >= PUBLIC_REACH 的索引算公共形态；contagion >= CONTAGION 算半公共
PUBLIC_REACH = 6
CONTAGION = 0.50
EPS = 1                                        # 汉明 <=1 视为同一个想法


def load():
    """返回 {label: 最后一根有效日线的记录}。"""
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as f:
        raw = json.load(f)
    rows = {}
    for name, v in raw.items():
        valid = [x for x in v["series"] if x["valid"]]
        if valid:
            rows[name] = valid[-1]
    return rows


def _stocks(rows):
    """剔除指数，只留个股。"""
    idx = {x.label for x in INDEX}
    return {k: v for k, v in rows.items() if k not in idx}


def global_map(stocks):
    """索引 -> (出现次数, 覆盖行业集合, 九维字符串)。"""
    count, secs = Counter(), defaultdict(set)
    sector_of = {x.label: x.sector for x in UNIVERSE}
    for k, v in stocks.items():
        i = v["index"]
        count[i] += 1
        secs[i].add(sector_of.get(k, "—"))
    return count, secs


def sectors(stocks, count, secs):
    """每个行业一行：n、众数索引、众数 reach、dup、contagion、标记。"""
    sector_of = {x.label: x.sector for x in UNIVERSE}
    by = defaultdict(list)
    for k, v in stocks.items():
        by[sector_of.get(k, "—")].append(v["index"])

    out = []
    for s, idxs in by.items():
        n = len(idxs)
        c = Counter(idxs)
        mode, mode_n = c.most_common(1)[0]
        dup = round(1 - len(c) / n, 3)
        reach = len(secs[mode])
        contagion = round(sum(1 for i in idxs if len(secs[i]) >= PUBLIC_REACH) / n, 2)
        if reach >= PUBLIC_REACH:
            flag = "公共形态"
        elif contagion >= CONTAGION:
            flag = "半公共"
        else:
            flag = "有区分度"
        out.append({
            "sector": s, "n": n, "mode_index": mode, "mode_str": vector_tostring(index_to_vector(mode)),
            "mode_n": mode_n, "mode_reach": reach, "dup": dup, "contagion": contagion,
            "indices": idxs, "flag": flag,
        })
    out.sort(key=lambda r: (-r["mode_reach"], -r["contagion"], r["dup"]))
    return out


def regimes(stocks):
    """按市场态分组：HHI 越高说明这个态在形态上是同一件事的复制。"""
    by = defaultdict(list)
    for v in stocks.values():
        by[v["regime"]].append(v["index"])
    out = []
    for r, idxs in by.items():
        n = len(idxs)
        c = Counter(idxs)
        hhi = round(sum((v / n) ** 2 for v in c.values()), 3)
        out.append({
            "regime": r, "n": n, "indices": len(c),
            "max_share": round(100 * c.most_common(1)[0][1] / n, 1),
            "hhi": hhi, "diversity": round(len(c) / n, 2),
        })
    out.sort(key=lambda r: -r["n"])
    return out


def independent(labels, index_of, eps=EPS):
    """并查集按汉明聚类，返回 [组...]，每组是标签列表。"""
    parent = {k: k for k in labels}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if hamming(index_of[a], index_of[b]) <= eps:
                union(a, b)

    groups = defaultdict(list)
    for k in labels:
        groups[find(k)].append(k)
    return sorted(groups.values(), key=len, reverse=True)


def pool(pairs):
    """候选池的名义数 vs 独立想法数。pairs = [(标签, 九维索引)]。"""
    if not pairs:
        return {"nominal": 0, "independent": 0, "groups": []}
    labels = [p[0] for p in pairs]
    raw_of = {p[0]: p[1] for p in pairs}
    index_of = {p[0]: index_to_vector(p[1]) for p in pairs}
    groups = independent(labels, index_of)
    return {
        "nominal": len(labels),
        "independent": len(groups),
        "groups": [{"members": g, "index": raw_of[g[0]], "hamming_in_group": max(
            (hamming(index_of[g[0]], index_of[m]) for m in g), default=0)} for g in groups],
    }


def build():
    rows = load()
    stocks = _stocks(rows)
    count, secs = global_map(stocks)
    data = {
        "universe": len(stocks),
        "distinct_indices": len(count),
        "top_attractors": [
            {
                "index": i, "count": c, "reach": len(secs[i]),
                "str": vector_tostring(index_to_vector(i)),
                "sectors": sorted(secs[i]),
            }
            for i, c in count.most_common(6)
        ],
        "sectors": sectors(stocks, count, secs),
        "regimes": regimes(stocks),
        "threshold": {"public_reach": PUBLIC_REACH, "contagion": CONTAGION, "eps": EPS},
    }
    return data, rows


def main():
    data, rows = build()
    with open(os.path.join(HERE, "out", "pipeline.json"), encoding="utf-8") as f:
        pipe = json.load(f)
    data["pool"] = pool([(p["short"], p["index"]) for p in pipe["picks"] if p["passed"]])
    with open(os.path.join(HERE, "out", "crowding.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("样本 %d 只 / %d 个索引（逐只多样 %.2f）"
          % (data["universe"], data["distinct_indices"], data["distinct_indices"] / data["universe"]))
    print("\n公共形态：")
    for a in data["top_attractors"]:
        if a["reach"] >= PUBLIC_REACH:
            print("  #%-6d %2d 只 reach=%d  %s  %s"
                  % (a["index"], a["count"], a["reach"], a["str"], "、".join(a["sectors"])))
    print("\n行业标记：")
    for s in data["sectors"]:
        if s["flag"] != "有区分度":
            print("  %-8s n=%d 众数 #%-6d reach=%d dup=%.2f contagion=%.2f %s"
                  % (s["sector"], s["n"], s["mode_index"], s["mode_reach"], s["dup"], s["contagion"], s["flag"]))
    print("\n市场态同构度：")
    for r in data["regimes"]:
        print("  %-6s %3d 只 / %2d 索引  HHI %.3f  最大占比 %.1f%%"
              % (r["regime"], r["n"], r["indices"], r["hhi"], r["max_share"]))
    print("\n候选池：名义 %d 只 -> 独立想法 %d 个（%.0f%%）"
          % (data["pool"]["nominal"], data["pool"]["independent"],
             100 * data["pool"]["independent"] / max(1, data["pool"]["nominal"])))
    for g in data["pool"]["groups"]:
        print("  「%s」 汉明组内最大 %d" % ("、".join(g["members"]), g["hamming_in_group"]))


if __name__ == "__main__":
    main()
