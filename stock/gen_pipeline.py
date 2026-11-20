"""把 pipeline.py 的结果渲染成流程页：docs/pipeline.html。

读 out/pipeline.json，不再重算。
"""

import json
import os
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")

STAGE = [
    ("L0", "市场状态", "两大指数九维 + 张力", "定总仓位"),
    ("L1", "行业轮动", "结构 · 方向 · 松紧", "选行业"),
    ("L2", "个股初筛", "确定度 · 张力 · 方向 · 实维", "选股"),
    ("L3", "结构确认", "正合 · 动量 · 波动", "定窗口"),
    ("L4", "组合去重", "同构合并 · 行业上限", "定仓"),
]


def stage_svg(res):
    f = res["funnel"]
    rows = [
        ("L0", "防守档", "2 个指数均空头确立", 2, 2, "pass"),
        ("L1", "3 / 6 行业", "张力过热 · 方向转负 · 样本不足", 3, 6, "cut"),
        ("L2", "5 / 24 只", "确定度 · 张力 · 方向 · 实维", f["个股"], f["样本"], "cut"),
        ("L3", "5 / 5 开窗", "正合同向 · 进≥0 · 守≠−1", f["入场"], max(1, f["个股"]), "pass"),
        ("L4", "3 只组合", "同构合并 · 单行业 ≤40%", f["组合"], max(1, f["进场"]) if "进场" in f else f["入场"], "pass"),
    ]
    w, top, rh = 380, 40, 46
    h = top + len(rows) * rh + 26
    p = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" '
         'aria-label="五层筛选流程：每层的保留数与拦截数">' % (w, h),
         "<style>.lb{fill:#e8e2d5;font-size:10px}.sb{fill:#87968f;font-size:8.5px}"
         ".vl{fill:#c8a45c;font-size:9px}.ps{fill:#5fa79b}.ct{fill:#b5452f}"
         ".tk{fill:#6b7a74}</style>",
         '<rect width="%d" height="%d" fill="#0f1a16"/>' % (w, h),
         '<text x="10" y="18" class="lb">五层筛选：每层留下什么，卡在哪一层</text>',
         '<text x="10" y="33" class="sb">条长 = 该层保留比例；灰段为被拦截部分</text>']
    x0, bw = 108, 200
    for i, (code, label, why, keep, total, kind) in enumerate(rows):
        y = top + i * rh
        ratio = keep / total if total else 0
        p.append('<text x="10" y="%g" class="lb">%s %s</text>' % (y + 14, code, label))
        p.append('<text x="%g" y="%g" class="sb">%s</text>' % (x0, y + 14, why))
        p.append('<rect x="%g" y="%g" width="%g" height="8" fill="#1b2723"/>' % (x0, y + 24, bw))
        p.append('<rect x="%g" y="%g" width="%g" height="8" rx="2" fill="%s"/>'
                 % (x0, y + 24, max(3, bw * ratio),
                    "#5fa79b" if kind == "pass" else "#b5452f"))
        p.append('<text x="%g" y="%g" class="vl" text-anchor="end">%d / %d</text>'
                 % (x0 + bw, y + 34, keep, total))
        if i < len(rows) - 1:
            p.append('<rect x="%g" y="%g" width="1" height="%g" fill="#24352f"/>'
                     % (x0 + 6, y + 32, rh - 24))
    p.append('<text x="10" y="%g" class="sb">青 = 该层通过　朱 = 有拦截</text>'
             % (top + len(rows) * rh + 12))
    p.append("</svg>")
    return "\n".join(p)


def sec_rows(res):
    out = []
    for s in res["sectors"]:
        cls = ' class="cut"' if s["veto"] else ""
        out.append("<tr%s><td>%s</td><td class=\"mono\">%d</td><td class=\"mono\">%.2f</td>"
                   "<td class=\"mono\">%+.2f</td><td class=\"mono\">%.2f</td>"
                   "<td class=\"mono\">%.3f</td><td>%s</td></tr>"
                   % (cls, s["sector"], s["n"], s["certain"], s["dir"],
                      s["median_tension"], s["score"],
                      ("拦截：" + s["reason"]) if s["veto"] else "候选"))
    return "\n".join(out)


def pick_rows(res):
    out = []
    for p in res["picks"]:
        LABEL = {"certain": "确定", "tension": "张力", "方向": "方向", "nz": "实维"}
        marks = "".join('<span class="g%s">%s</span>' % ("y" if v else "n", LABEL.get(k, k))
                        for k, v in p["gate"].items())
        cls = ' class="hl"' if p["passed"] and p["window"] else (
            ' class="cut"' if not p["passed"] else "")
        out.append("<tr%s><td>%s</td><td>%s</td><td class=\"mono\">%d/9</td>"
                   "<td class=\"mono\">%.2f</td><td class=\"mono\">%d</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (cls, p["short"], p["sector"], p["certain"], p["tension"],
                      p["nz"], marks, "开" if p["window"] else "关"))
    return "\n".join(out)


def main():
    with open(os.path.join(HERE, "out", "pipeline.json"), encoding="utf-8") as f:
        res = json.load(f)
    f = res["funnel"]
    port = "、".join(k["short"] for k in res["portfolio"])
    t = Template(TPL).substitute(
        level=res["regime"]["level"], cap=res["regime"]["caps"],
        sh_t="%.2f" % res["regime"]["indices"][0]["tension"],
        hs_t="%.2f" % res["regime"]["indices"][1]["tension"],
        nsec=len([s for s in res["sectors"] if not s["veto"]]),
        npick=f["个股"], nwin=f["入场"], nport=f["组合"], nsample=f["样本"],
        svg=stage_svg(res), sec_rows=sec_rows(res), pick_rows=pick_rows(res),
        port=port or "空仓")
    html = t
    for path in (os.path.join(HERE, "pipeline_report.html"), os.path.join(DOCS, "pipeline.html")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("wrote", path)


TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>五层漏斗：从市场状态到退出条件</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%230b1210'/%3E%3Crect x='10' y='10' width='44' height='8' fill='%235fa79b'/%3E%3Crect x='16' y='26' width='32' height='8' fill='%23c8a45c'/%3E%3Crect x='22' y='42' width='20' height='8' fill='%23b5452f'/%3E%3C/svg%3E">
<style>
:root{--ink:#0b1210;--panel:#0f1a16;--line:#24352f;--fog:#e8e2d5;--dim:#87968f;
--jade:#5fa79b;--cinn:#b5452f;--gold:#c8a45c;--mid:#6b7a74}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--ink);color:var(--fog);
font-family:'Songti SC','Noto Serif CJK SC','Source Han Serif SC',serif;
font-size:16px;line-height:1.85;-webkit-font-smoothing:antialiased}
.wrap{max-width:820px;margin:0 auto;padding:56px 24px 80px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.eyebrow{color:var(--gold);font-size:12px;letter-spacing:.22em}
h1{font-size:33px;line-height:1.25;font-weight:600;margin:14px 0 10px}
.lead{color:var(--dim);font-size:15.5px;max-width:650px}
.bar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);
border:1px solid var(--line);margin:30px 0}
.bar div{background:var(--panel);padding:16px 14px}
.bar b{display:block;font-size:25px;line-height:1.2;font-family:ui-monospace,monospace}
.bar span{display:block;color:var(--dim);font-size:12px;margin-top:4px}
.bar b.c{color:var(--cinn)}.bar b.j{color:var(--jade)}.bar b.g{color:var(--gold)}
h2{font-size:19px;font-weight:600;margin:40px 0 14px}
h2::before{content:"";display:inline-block;width:3px;height:15px;background:var(--gold);
vertical-align:-2px;margin-right:10px}
p{margin:0 0 14px;color:#cfd6cf}
figure{margin:24px 0;max-width:640px}
figure svg{width:100%;height:auto;display:block;border:1px solid var(--line)}
figcaption{color:var(--dim);font-size:12.5px;margin-top:10px;line-height:1.7}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;table-layout:fixed}
.s1{width:20%}.s2{width:10%}.s3{width:12%}.s4{width:12%}.s5{width:14%}.s6{width:12%}.s7{width:22%}
.p1{width:18%}.p2{width:15%}.p3{width:11%}.p4{width:11%}.p5{width:9%}.p6{width:24%}.p7{width:12%}
th{color:var(--dim);font-weight:500;font-size:12px;text-align:left;
padding:8px 6px;border-bottom:1px solid var(--line)}
td{padding:9px 6px;border-bottom:1px solid #1a2723;color:#c9d1ca}
td.mono{font-size:12.5px}
tr.cut td{color:#6b7a74}
tr.hl td{color:var(--gold)}
.gy{color:var(--jade);margin-right:6px}.gn{color:#6b7a74;margin-right:6px;text-decoration:line-through}
@media(max-width:860px){.gy,.gn{margin-right:3px}}
.note{background:var(--panel);border-left:3px solid var(--jade);padding:18px 20px;margin:20px 0}
.note .k{color:var(--jade);font-size:12px;letter-spacing:.14em;display:block;margin-bottom:6px}
.warn{border-left-color:var(--cinn)}.warn .k{color:var(--cinn)}
ul{padding-left:22px;margin:0 0 14px}li{margin-bottom:8px;color:#cfd6cf}
li b{color:var(--fog);font-weight:600}
.foot{color:var(--mid);font-size:12.5px;line-height:1.9;border-top:1px solid var(--line);
padding-top:20px;margin-top:44px}
a{color:var(--jade);text-decoration:none;border-bottom:1px dotted #2c4740;white-space:nowrap}
@media(max-width:860px){
.wrap{padding:40px 18px 60px}h1{font-size:26px}
.bar{grid-template-columns:1fr 1fr}
table{font-size:12px}th{font-size:11px}th,td{padding:7px 4px}
td.mono{font-size:11px}
.s1{width:19%}.s2{width:9%}.s3{width:11%}.s4{width:11%}.s5{width:15%}.s6{width:12%}.s7{width:24%}
.p1{width:17%}.p2{width:14%}.p3{width:10%}.p4{width:10%}.p5{width:10%}.p6{width:25%}.p7{width:14%}
}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">润泽说 · 认知生命体 v9 · 流程</div>
<h1>五层漏斗</h1>
<p class="lead">自上而下五层，每层只回答一个问题，每层都能拦人。今天的答案是：<b>市场防守档，六个行业剩三个，
24 只样本剩 5 只，收成 3 只组合。</b></p>

<div class="bar">
<div><b class="c">$level</b><span>市场状态 · 仓位 $cap</span></div>
<div><b class="g">$nsec / 6</b><span>候选行业</span></div>
<div><b class="j">$npick / $nsample</b><span>过筛个股</span></div>
<div><b class="j">$nport</b><span>组合持仓</span></div>
</div>

<figure>
$svg
<figcaption>先定市场档位，再定行业，再定个股，最后合并成组合。条长是该层保留比例，
不是收益率。L2 卡在最狠处——24 只只过 5 只。</figcaption>
</figure>

<h2>一、L0 市场状态：防守</h2>
<p>两个指数<b>同时空头确立</b>：上证 #186、7/9 确定、张力 $sh_t；沪深300 #21、5/9、张力 $hs_t。
两条都越过 0.65 的防守线——这一层的结论不是"哪个行业好"，而是<b>总仓位压到三成以内</b>，
只允许结构性机会，不做行业轮动式加仓。</p>
<p>顺序不能颠倒。行业分再高，在防守档里也只能小仓试，这是流程与选股清单最大的差别。</p>

<h2>二、L1 行业轮动：六个剩三个</h2>
<p>每个行业按三件事打分：<b>结构分</b>（确定度均值）、<b>方向分</b>（多头占比减空头占比）、
<b>松紧分</b>（1 − 中位张力）。加权 0.4／0.4／0.2。任何一项越界就拦截，不看总分排名。</p>
<table>
<colgroup><col class="s1"><col class="s2"><col class="s3"><col class="s4"><col class="s5"><col class="s6"><col class="s7"></colgroup>
<thead><tr><th>行业</th><th>样本</th><th>结构</th><th>方向</th><th>中位张力</th><th>得分</th><th>结论</th></tr></thead>
<tbody>
$sec_rows
</tbody>
</table>
<div class="note warn">
<span class="k">三条拦截理由，各有各的意思</span>
石油石化中位张力 0.67 —— 不是不涨，是波动已经压不住；化工方向分 −0.62 —— 八只里五只空头确立，
方向一致朝下；<b>公用事业只有长江电力一只</b> —— 它 9/9 满维、张力 0.50，单看很好，
但一只代表不了一个行业，样本不足就不入选。这条规则宁可漏，不可错。
</div>

<h2>三、L2 个股初筛：24 只过 5 只</h2>
<p>在候选行业里逐只过四关：<b>确定度 ≥ 5</b>（不足半数维有值就不信）、<b>张力 ≤ 0.55</b>、
<b>方向</b>（按位置分流，见下）、<b>实维 ≤ 7</b>（8 维以上说明结构已结晶，没有"未定"空间可赚）。</p>
<div class="note">
<span class="k">方向这关差点写错</span>
第一版把「归 = −1」直接当否决项，结果 24 只全灭——因为这些标的都站在 20 日区间 87–100% 分位。
上沿不是坏位置，单边上涨的股票永远在上沿。改成<b>分流</b>：位置高（−1）走右侧，要看动量还在（进 ≥ 0）；
位置低（+1）走左侧，要看均线转同向；中段看合力。同一条数据，换个问法，结论就活了。
</div>
<table>
<colgroup><col class="p1"><col class="p2"><col class="p3"><col class="p4"><col class="p5"><col class="p6"><col class="p7"></colgroup>
<thead><tr><th>标的</th><th>行业</th><th>确定</th><th>张力</th><th>实维</th><th>四关</th><th>窗口</th></tr></thead>
<tbody>
$pick_rows
</tbody>
</table>
<p style="color:#87968f;font-size:13px">划掉的关是没过的。兴业、浦发、北京、陕煤都倒在"实维 ≤ 7"——
它们不是弱，是<b>已经走完</b>，八维全填满，没有可赚的"未定"。</p>

<h2>四、L3 结构确认：过筛的 5 只全部开窗</h2>
<p>过了筛还要等窗口——表里未过筛的即使窗口开着也不算候选：<b>正/合同向</b>（均线与动量同向）、<b>进 ≥ 0</b>（5 日动量不为负）、
<b>守 ≠ −1</b>（当日振幅没放大）。5 只全部满足——说明今天的瓶颈不在时机，在结构。</p>

<h2>五、L4 组合去重：5 只收成 3 只</h2>
<p>汉明距离 ≤ 1 的两只视为同构，只留确定度高、张力低的一只。招商、中国平安、长江电力
三只累积态<b>完全相同</b>（#17312、9/9、0 悬置），只留张力最低的招商；工商 #17311 差一维，一并合并。</p>
<p>最后剩下 <b>$port</b>，跨三个行业，单一行业权重不超过 40%。在防守档里，这就是上限。</p>

<h2>六、L5 退出：三条，任一触发就走</h2>
<ul>
<li><b>掉维。</b>确定度一次降 2 维及以上——证据在散，不是价格在跌。</li>
<li><b>张力破 0.65。</b>波动负荷与跌破深度同时咬住，结构已经不可维持。</li>
<li><b>与领头羊翻转数 +1。</b>和组合内最强那只出现新的方向对立，说明分化开始。</li>
</ul>
<p>退出条件写在选股之前，是流程和"看情况再说"的分界线。</p>

<h2>七、这套流程缺什么</h2>
<div class="note warn">
<span class="k">只覆盖了一条轴，说清楚免得误用</span>
五层的骨架是完整的，但引擎只吃价格行为这一条轴。下面这些全部空缺，<b>流程里没有任何一步替它们做判断</b>：
<ul style="margin-top:8px">
<li>基本面：ROE、现金流、负债率、存货与应收周转 —— 未接入</li>
<li>资金流：北向、融资余额、龙虎榜、大宗 —— 未接入</li>
<li>盈利预期：分析师上修/下修、业绩预告 —— 未接入</li>
<li>市场广度：涨跌家数、新高新低、成交额分布 —— L0 只用两大指数代替</li>
<li>行业覆盖：31 个申万一级行业只取了 6 个，代表股 1–9 只不等</li>
<li>事件与交易约束：财报窗口、停牌、涨跌停、除权 —— 未处理</li>
<li>估值：只有 9 只银行有 PB/PE，其余空白</li>
</ul>
</div>
<p>补齐的顺序应该是：先补行业覆盖（把 31 个行业各取 3–5 只代表），再补广度与资金流（L0、L1 才有分母），
最后才是基本面与预期（L2 才谈得上"好公司"）。跳过前两步直接谈基本面，是把流程当清单用。</p>

<div class="foot">
样本：24 只个股（9 银行 + 8 化工 + 2 保险 + 2 煤炭 + 2 石油石化 + 1 公用事业）+ 上证 + 沪深300，
2026-10-16 至 11-20 共 26 根日 K，引擎取 21 个有效状态。行情取自新浪财经日线接口。<br>
判据阈值全部写在 <span class="mono">stock/pipeline.py</span> 的 THRESHOLD 里，改一处即改流程。<br>
本文是结构诊断，不是投资建议。流程能筛掉没有证据的判断，筛不掉基本面风险。<br>
引擎 repo：<a href="https://github.com/q1z2q3-debug/cognitive-being-v9">cognitive-being-v9</a>
　·　<a href="./index.html">返回主页</a>　·　<a href="./chem.html">化工读数</a>
　·　<a href="./rank.html">跨行业排名</a>　·　<a href="./bank-scan.html">同业扫描</a>
</div>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
