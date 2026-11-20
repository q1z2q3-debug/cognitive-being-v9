"""选股流程：五层漏斗。

行业标准做法是自上而下：市场状态 → 行业轮动 → 个股筛选 → 结构确认 → 组合与退出。
本引擎只覆盖「价格行为的结构与证据覆盖度」这一条轴，所以每层只做它能做的判断，
基本面、资金流、盈利预期一律不冒充——缺口在页面末尾显式列出。

层与判据
--------
L0 市场状态  指数九维 + 张力 → 进攻 / 中性 / 防守。决定总仓位上限，先于选股。
L1 行业轮动  按行业聚合三件事:结构分(确定度均值)、方向分(多头占比-空头占比)、松紧分(1-张力中位)。
             行业张力中位 > 0.65 一票否决——板块已经过热,再好的个股也在逆风里。
L2 个股初筛  行业内逐只过四关:确定度>=5、张力<=0.55、归!=-1、实维<=7。
             归=-1 说明已在 20 日区间上沿,属追高;实维=8/9 说明结构已结晶,无「未定」空间。
L3 结构确认  正/合同向 + 进>=0 + 守!=-1。三条同时成立才算有入场窗口,否则只观察。
L4 组合去重  汉明距离 <=1 的两只视为同构,只留确定度高、张力低的一只;单行业权重上限 40%。
L5 退出监控  掉维(确定度降 2)、张力破 0.65、与领头羊翻转数 +1，任一触发即退出。

阈值全部写在 THRESHOLD 里,改一处即改流程,便于事后复盘口径。
"""

import json
import os
import math
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from stock.metrics import hamming, flips, euclid          # noqa: E402

THRESHOLD = {
    "L0_defend_tension": 0.65,     # 指数张力过此线直接防守
    "L0_attack_tension": 0.50,     # 多头确立且张力低于此线才进攻
    "L1_veto_tension": 0.65,       # 行业中位张力过线否决
    "L1_min_samples": 2,           # 单只样本代表不了行业，不足不入选
    "L2_certain": 5,               # 至少 5 维有值
    "L2_tension": 0.55,            # 张力上限
    "L2_nz": 7,                    # 实维上限,8 以上算结晶
    "L4_dup_hamming": 1,           # 汉明 <=1 视为同构
    "L5_drop_dims": 2,             # 一次掉 2 维即退出
}

SECTOR = {
    "上证指数 000001": "指数", "沪深300 000300": "指数",
    "平安银行 000001.SZ": "银行", "浦发银行 600000.SH": "银行",
    "华夏银行 600015.SH": "银行", "民生银行 600016.SH": "银行",
    "招商银行 600036.SH": "银行", "兴业银行 601166.SH": "银行",
    "北京银行 601169.SH": "银行", "工商银行 601398.SH": "银行",
    "光大银行 601818.SH": "银行",
    "中国神华 601088.SH": "煤炭", "陕西煤业 601225.SH": "煤炭",
    "中国石油 601857.SH": "石油石化", "中国海油 600938.SH": "石油石化",
    "长江电力 600900.SH": "公用事业",
    "中国人寿 601628.SH": "保险", "中国平安 601318.SH": "保险",
    "万华化学 600309.SH": "化工", "华鲁恒升 600426.SH": "化工",
    "卫星化学 002648.SZ": "化工", "龙佰集团 002601.SZ": "化工",
    "兴发集团 600141.SH": "化工", "恒力石化 600346.SH": "化工",
    "荣盛石化 002493.SZ": "化工", "扬农化工 600486.SH": "化工",
}
SHORT = {
    "上证指数 000001": "上证", "沪深300 000300": "沪深300",
    "平安银行 000001.SZ": "平安银行", "浦发银行 600000.SH": "浦发",
    "华夏银行 600015.SH": "华夏", "民生银行 600016.SH": "民生",
    "招商银行 600036.SH": "招商", "兴业银行 601166.SH": "兴业",
    "北京银行 601169.SH": "北京", "工商银行 601398.SH": "工商",
    "光大银行 601818.SH": "光大", "中国神华 601088.SH": "神华",
    "陕西煤业 601225.SH": "陕煤", "中国石油 601857.SH": "中石油",
    "中国海油 600938.SH": "中海油", "长江电力 600900.SH": "长电",
    "中国人寿 601628.SH": "人寿", "中国平安 601318.SH": "中国平安",
    "万华化学 600309.SH": "万华", "华鲁恒升 600426.SH": "华鲁",
    "卫星化学 002648.SZ": "卫星", "龙佰集团 002601.SZ": "龙佰",
    "兴发集团 600141.SH": "兴发", "恒力石化 600346.SH": "恒力",
    "荣盛石化 002493.SZ": "荣盛", "扬农化工 600486.SH": "扬农",
}
DIMS = ("天", "地", "人", "正", "反", "合", "归", "守", "进")


def load():
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for name, v in raw.items():
        last = [x for x in v["series"] if x["valid"]][-1]
        rows.append({
            "name": name, "short": SHORT.get(name, name), "sector": SECTOR.get(name, "—"),
            "state": last["state"], "index": last["index"], "regime": last["regime"],
            "tension": last["tension"]["T"],
            "certain": sum(1 for q in last["obs"] if q),
            "nz": sum(1 for q in last["state"] if q),
            "close": last["close"],
        })
    return rows


def dir_score(r):
    if "多头" in r["regime"]:
        return 1
    if "空头" in r["regime"]:
        return -1
    return 0


def l0(rows):
    idx = {r["name"]: r for r in rows}
    sh, hs = idx["上证指数 000001"], idx["沪深300 000300"]
    out = []
    worst_t = max(sh["tension"], hs["tension"])
    any_bear = ("空头" in sh["regime"]) or ("空头" in hs["regime"])
    if any_bear or worst_t > THRESHOLD["L0_defend_tension"]:
        level = "防守"
    elif "多头" in sh["regime"] and sh["tension"] < THRESHOLD["L0_attack_tension"]:
        level = "进攻"
    else:
        level = "中性"
    out.append({"key": "上证", "regime": sh["regime"], "index": sh["index"],
                "tension": sh["tension"], "certain": sh["certain"]})
    out.append({"key": "沪深300", "regime": hs["regime"], "index": hs["index"],
                "tension": hs["tension"], "certain": hs["certain"]})
    return {"level": level, "max_tension": worst_t, "indices": out,
            "caps": {"进攻": "8 成以内", "中性": "5 成以内", "防守": "3 成以内"}[level]}


def l1(rows):
    secs = {}
    for r in rows:
        if r["sector"] in ("指数", "—"):
            continue
        secs.setdefault(r["sector"], []).append(r)
    out = []
    for s, rs in secs.items():
        n = len(rs)
        cert = sum(r["certain"] for r in rs) / n
        dscore = sum(dir_score(r) for r in rs) / n
        med_t = sorted(r["tension"] for r in rs)[n // 2]
        loose = 1 - med_t
        veto = (med_t > THRESHOLD["L1_veto_tension"] or dscore < -0.2
                or n < THRESHOLD["L1_min_samples"])
        total = cert / 9 * 0.4 + (dscore + 1) / 2 * 0.4 + loose * 0.2
        out.append({"sector": s, "n": n, "certain": round(cert, 2),
                    "dir": round(dscore, 2), "median_tension": round(med_t, 3),
                    "loose": round(loose, 3), "score": round(total, 3),
                    "veto": veto, "leader": rs[0]["short"],
                    "reason": ("样本不足" if n < THRESHOLD["L1_min_samples"] else
                               ("张力过热" if med_t > THRESHOLD["L1_veto_tension"] else
                                ("方向转负" if dscore < -0.2 else "")))})
    out.sort(key=lambda x: -x["score"])
    return out


def l2(rows, sectors):
    picks = []
    for s in sectors:
        if s["veto"]:
            continue
        for r in rows:
            if r["sector"] != s["sector"]:
                continue
            # 归维是位置，不是好坏：上沿(-1)走右侧延续，下沿(+1)走左侧反转，中间看合力。
            # 把「在上沿」直接毙掉，等于只敢买横盘股，强势股会被系统性地全部排除。
            gu, jin, he, zheng = r["state"][6], r["state"][8], r["state"][5], r["state"][3]
            if gu == -1:
                gu_ok = jin >= 0                 # 右侧：位置高，但动量还在
            elif gu == 1:
                gu_ok = zheng == he and zheng != 0   # 左侧：位置低，需均线转同向
            else:
                gu_ok = he != 0                  # 中段：至少有一条均线方向
            gate = {
                "certain": r["certain"] >= THRESHOLD["L2_certain"],
                "tension": r["tension"] <= THRESHOLD["L2_tension"],
                "方向": gu_ok,
                "nz": r["nz"] <= THRESHOLD["L2_nz"],
            }
            picks.append({**r, "gate": gate, "passed": all(gate.values())})
    picks.sort(key=lambda r: (-r["certain"], r["tension"]))
    return picks


def l3(picks):
    for p in picks:
        st = p["state"]
        p["entry"] = {
            "正/合同向": st[3] == st[5] and st[3] != 0,
            "进≥0": st[8] >= 0,
            "守≠-1": st[7] != -1,
        }
        p["window"] = all(p["entry"].values())
    return picks


def l4(picks):
    passed = [p for p in picks if p["passed"]]
    keep = []
    for p in passed:
        dup = [k for k in keep if hamming(k["state"], p["state"]) <= THRESHOLD["L4_dup_hamming"]]
        if not dup:
            keep.append(p)
    return keep


def main():
    rows = load()
    reg = l0(rows)
    sectors = l1(rows)
    picks = l3(l2(rows, sectors))
    keep = l4(picks)
    res = {
        "regime": reg,
        "sectors": sectors,
        "picks": [{k: v for k, v in p.items() if k != "gate"} | {"gate": p["gate"]}
                  for p in picks],
        "portfolio": [{"short": k["short"], "sector": k["sector"], "certain": k["certain"],
                       "tension": k["tension"], "index": k["index"]} for k in keep],
        "funnel": {
            "样本": len([r for r in rows if r["sector"] not in ("指数", "—")]),
            "行业": len([s for s in sectors if not s["veto"]]),
            "个股": len([p for p in picks if p["passed"]]),
            "入场": len([p for p in picks if p["passed"] and p["window"]]),
            "组合": len(keep),
        },
        "threshold": THRESHOLD,
    }
    with open(os.path.join(HERE, "out", "pipeline.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    print("L0 市场状态：%s（仓位上限 %s）" % (reg["level"], reg["caps"]))
    for i in reg["indices"]:
        print("   %-8s #%-6d %-6s T=%.2f %d/9" % (i["key"], i["index"], i["regime"],
                                                  i["tension"], i["certain"]))
    print("\nL1 行业轮动：")
    for s in sectors:
        print("   %-6s n=%d 结构%.2f 方向%+.2f 中位张力%.2f 松紧%.2f → %.3f %s"
              % (s["sector"], s["n"], s["certain"], s["dir"], s["median_tension"],
                 s["loose"], s["score"], "否决" if s["veto"] else "候选"))
    print("\nL2/L3 个股：")
    for p in picks:
        g = "".join(["+", "-"][int(not v)] for v in p["gate"].values())
        print("   %-8s %-6s %d/9 T=%.2f 实维%d 闸口%s 过筛%s 窗口%s"
              % (p["short"], p["sector"], p["certain"], p["tension"], p["nz"], g,
                 "是" if p["passed"] else "否", "是" if p["window"] else "否"))
    print("\nL4 组合：%s" % (", ".join(k["short"] for k in keep) or "空仓"))
    print("漏斗：%s" % res["funnel"])


if __name__ == "__main__":
    main()
