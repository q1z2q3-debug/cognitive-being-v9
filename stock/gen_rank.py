"""跨行业维度排名 → docs/rank.html。

标的来自 stock/universe.py 与 out/stock_state.json；只取每个行业的榜首做横向比较，
全量 124 只的逐只读数在 pipeline 页的 L2 表里。
"""

import json
import os
import sys
from collections import Counter
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")
sys.path.insert(0, os.path.dirname(HERE))

from stock.universe import UNIVERSE  # noqa: E402

by_label = {a.label: a for a in UNIVERSE}
VOL15 = {"浦发银行 600000.SH": (6.99, 0.477), "华夏银行 600015.SH": (4.48, 0.331),
         "民生银行 600016.SH": (5.77, 0.264), "招商银行 600036.SH": (7.26, 0.939),
         "兴业银行 601166.SH": (5.72, 0.505), "北京银行 601169.SH": (6.20, 0.455),
         "工商银行 601398.SH": (8.72, 0.836), "光大银行 601818.SH": (6.38, 0.373),
         "平安银行 000001.SZ": (5.45, 0.498)}


def load():
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for name, v in raw.items():
        last = [x for x in v["series"] if x["valid"]][-1]
        a = by_label.get(name)
        rows.append({
            "name": name,
            "short": a.short if a else name,
            "sector": a.sector if a else "—",
            "state": last["state"],
            "index": last["index"],
            "regime": last["regime"],
            "tension": last["tension"]["T"],
            "certain": sum(1 for q in last["obs"] if q),
        })
    rows.sort(key=lambda r: (-r["certain"], r["tension"], r["short"]))
    return rows


def leaders(rows):
    """每个行业里确定度最高、张力最低的那只。"""
    out = {}
    for r in rows:
        if r["sector"] in ("指数", "—"):
            continue
        if r["sector"] not in out:
            out[r["sector"]] = r
    return sorted(out.values(), key=lambda r: (-r["certain"], r["tension"]))


def tone(regime):
    if "多头" in regime:
        return "pos"
    if "空头" in regime:
        return "neg"
    return "neu"


def tag(regime):
    if "多头" in regime:
        return "多头"
    if "空头" in regime:
        return "空头"
    if "弱" in regime:
        return "弱定向"
    return "对峙"


def make_svg(leads):
    w, top, rh = 436, 46, 19
    h = top + len(leads) * rh + 36
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" '
        'aria-label="%d 个申万一级行业榜首的九维确定度排序">' % (w, h, len(leads)),
        "<style>.tl{fill:#e8e2d5;font-size:10.5px}.hd{fill:#87968f;font-size:9px}"
        ".nm{fill:#c9d1ca;font-size:9.5px}.sec{fill:#7f8f88;font-size:9px}"
        ".tg{fill:#87968f;font-size:9px}"
        ".pos{fill:#5fa79b}.neg{fill:#b5452f}.neu{fill:#6b7a74}</style>",
        '<rect width="%d" height="%d" fill="#0f1a16"/>' % (w, h),
        '<text x="10" y="18" class="tl">%d 个行业榜首的九维确定度（9 格全满 = 每一维都有依据）</text>'
        % len(leads),
        '<text x="126" y="34" class="hd">1</text>',
        '<text x="302" y="34" class="hd" text-anchor="end">9</text>',
        '<text x="354" y="34" class="hd" text-anchor="end">张力</text>',
        '<text x="428" y="34" class="hd" text-anchor="end">态</text>',
    ]
    x0, cw, gap = 126, 18, 2
    for i, r in enumerate(leads):
        y = top + i * rh
        if r["certain"] == 9:
            parts.append('<rect x="4" y="%g" width="428" height="%g" fill="#5fa79b" opacity=".09"/>'
                         % (y, rh - 2))
        parts.append('<text x="8" y="%g" class="nm">%s</text>' % (y + 12, r["short"]))
        parts.append('<text x="54" y="%g" class="sec">%s</text>'
                     % (y + 12, r["sector"]))
        for k in range(9):
            cx = x0 + k * (cw + gap)
            fill = "class=\"%s\" opacity=\".85\"" % tone(r["regime"]) if k < r["certain"] else 'fill="#1b2723"'
            parts.append('<rect x="%g" y="%g" width="%g" height="12" rx="1.5" %s/>'
                         % (cx, y + 2, cw, fill))
        parts.append('<text x="354" y="%g" class="tg" text-anchor="end">%.2f</text>'
                     % (y + 12, r["tension"]))
        parts.append('<text x="428" y="%g" class="tg" text-anchor="end">%s</text>'
                     % (y + 12, tag(r["regime"])))
    nf = len([r for r in leads if r["certain"] == 9])
    parts.append('<text x="10" y="%g" class="hd">青 = 多头　灰 = 对峙　朱 = 空头　　'
                 '高亮 %d 个行业榜首满维</text>' % (top + len(leads) * rh + 16, nf))
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    rows = load()
    leads = leaders(rows)
    full = [r for r in rows if r["certain"] == 9]
    fl = [r for r in full if "多头" in r["regime"]]
    fs = [r for r in full if "空头" in r["regime"]]
    fn = [r for r in full if "多头" not in r["regime"] and "空头" not in r["regime"]]
    nlong = len([r for r in rows if "多头" in r["regime"]])
    nshort = len([r for r in rows if "空头" in r["regime"]])
    low_t = [r for r in full if r["tension"] <= 0.60]
    high_t = [r for r in full if r["tension"] >= 0.70]
    c = Counter(r["index"] for r in leads)
    top_idx, top_n = c.most_common(1)[0]
    top_sec = [r["sector"] for r in leads if r["index"] == top_idx]
    big = [(i, n) for i, n in c.most_common(2) if n >= 3]
    grp = []
    for idx, n in big:
        names = [r["short"] for r in leads if r["index"] == idx]
        grp.append("#%d 的 %d 只（%s）" % (idx, n, "、".join(names)))

    trs = []
    for r in leads:
        cls = ' class="hl"' if r["certain"] == 9 else ""
        same = c[r["index"]]
        trs.append("<tr%s><td>%s</td><td>%s</td><td class=\"mono\">#%d</td><td>%s</td>"
                   "<td class=\"mono\">%d/9</td><td class=\"mono\">%.2f</td><td>%s</td></tr>"
                   % (cls, r["short"], r["sector"], r["index"], tag(r["regime"]),
                      r["certain"], r["tension"],
                      str(same) if same >= 3 else "—"))
    html = TEMPLATE.substitute(
        nlead=len(leads), nall=len(rows), nfull=len(full),
        nfl=len(fl), nfs=len(fs), nfn=len(fn),
        nlong=nlong, nshort=nshort,
        svg=make_svg(leads), rows="\n".join(trs),
        grp="；".join(grp),
        fl_names="、".join(r["short"] for r in fl),
        fs_names="、".join(r["short"] for r in fs),
        nlt=len(low_t), nltl=len([r for r in low_t if "多头" in r["regime"]]),
        nht=len(high_t), nhts=len([r for r in high_t if "空头" in r["regime"]]),
        top_idx=top_idx, top_n=top_n, top_sec="、".join(top_sec))
    for path in (os.path.join(HERE, "rank_report.html"), os.path.join(DOCS, "rank.html")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("wrote", path)
    for r in leads:
        print("%-7s %-7s %d/9 %.2f %s #%d" % (r["short"], r["sector"], r["certain"],
                                              r["tension"], tag(r["regime"]), r["index"]))


TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>31 个行业榜首 · 跨行业九维排名</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%230b1210'/%3E%3Crect x='8' y='8' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='25' y='8' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='42' y='8' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='8' y='25' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='25' y='25' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='42' y='25' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='8' y='42' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='25' y='42' width='14' height='14' fill='%235fa79b'/%3E%3Crect x='42' y='42' width='14' height='14' fill='%235fa79b'/%3E%3C/svg%3E">
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
h1{font-size:34px;line-height:1.25;font-weight:600;margin:14px 0 10px}
.lead{color:var(--dim);font-size:15.5px;max-width:660px}
.bar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);
border:1px solid var(--line);margin:32px 0}
.bar div{background:var(--panel);padding:16px 14px}
.bar b{display:block;font-size:26px;line-height:1.2;font-family:ui-monospace,monospace}
.bar span{display:block;color:var(--dim);font-size:12px;margin-top:4px}
.bar b.j{color:var(--jade)}.bar b.g{color:var(--gold)}.bar b.c{color:var(--cinn)}
h2{font-size:19px;font-weight:600;margin:40px 0 14px}
h2::before{content:"";display:inline-block;width:3px;height:15px;background:var(--gold);
vertical-align:-2px;margin-right:10px}
p{margin:0 0 14px;color:#cfd6cf}
figure{margin:26px 0;max-width:640px}
figure svg{width:100%;height:auto;display:block;border:1px solid var(--line)}
figcaption{color:var(--dim);font-size:12.5px;margin-top:10px;line-height:1.7}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px;table-layout:fixed}
.c1{width:14%}.c2{width:15%}.c3{width:18%}.c4{width:17%}.c5{width:10%}.c6{width:11%}.c7{width:15%}
th{color:var(--dim);font-weight:500;font-size:12px;text-align:left;
padding:8px 6px;border-bottom:1px solid var(--line)}
td{padding:9px 6px;border-bottom:1px solid #1a2723;color:#c9d1ca}
td.mono{font-size:12.5px}
tr.hl td{color:var(--gold)}
.note{background:var(--panel);border-left:3px solid var(--jade);padding:18px 20px;margin:22px 0}
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
.c1{width:16%}.c2{width:19%}.c3{width:18%}.c4{width:14%}.c5{width:9%}.c6{width:10%}.c7{width:14%}
}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">润泽说 · 认知生命体 v9 · 引擎读数</div>
<h1>$nfull 只满维，$nfl 只方向也朝上</h1>
<p class="lead">$nall 只个股、$nlead 个申万一级行业，塞进同一把九维尺子。不看行业，只看谁能把九个格子全部填满——<b>然后看它的方向。</b></p>

<div class="bar">
<div><b class="g">$nlead</b><span>行业榜首</span></div>
<div><b class="j">$nfull</b><span>九维全满</span></div>
<div><b class="c">$nshort</b><span>空头确立</span></div>
<div><b class="j">$nlong</b><span>多头确立</span></div>
</div>

<figure>
$svg
<figcaption>每行是一个行业的榜首，格数即「观测层有明确值的维度数」，剩余为悬置。
高亮行是 0 悬置的满维标的。</figcaption>
</figure>

<h2>一、满格不等于方向对</h2>
<p>$nall 只个股里，$nfull 只把九维填满。拆开看：<b>$nfl 只多头确立</b>（$fl_names）、
<b>$nfs 只空头确立</b>（$fs_names）、其余 $nfn 只弱定向。</p>
<p>这是这套尺子最容易被误读的地方。九维衡量的是<b>「价格行为被证据覆盖的程度」</b>，
不是方向。一只股票可以每一天都有明确依据地往下跌——那它也会是 9/9。
满维的 $nfs 只就是这种形态：证据充分、方向朝下、张力还高。</p>

<h2>二、同一个索引，可以横跨四个行业</h2>
<p>$grp。九维不认行业，只认形态。银行、公用事业、非银金融、通信四个不相干的板块，
可以落进同一个状态码——所以「维度最佳」问的不是哪个行业好，而是谁的每一个判断都有证据。</p>
<div class="note">
<span class="k">这条比名单重要</span>
同一个状态在四个行业出现，说明这个状态描述的是<b>市场结构</b>，不是公司质地。
反过来，一个行业里挤满了同一个索引（化工、美容、传媒、社服、纺服全是 #183），
说明这个板块已经走成一条线了，没有分化，也就没有个股 alpha。
</div>

<h2>三、$nlead 个行业的榜首</h2>
<table>
<colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6"><col class="c7"></colgroup>
<thead><tr><th>标的</th><th>行业</th><th>索引</th><th>市场态</th><th>确定</th><th>张力</th><th>同构数</th></tr></thead>
<tbody>
$rows
</tbody>
</table>
<p style="color:#87968f;font-size:13px">「同构数」= 在这 $nlead 个行业榜首里，落在同一索引的只数（≥3 才标）。
确定 = 观测层有值的维度数；张力 = 0.4 波动负荷 + 0.3 跌破 MA20 深度 + 0.3 状态抖动。</p>

<h2>四、张力分层比确定度更管用</h2>
<ul>
<li><b>满维且张力 ≤ 0.60：$nlt 只，其中 $nltl 只多头确立。</b>
证据齐全、波动也没咬住，这是今天唯一「既有依据又不难受」的一组。</li>
<li><b>满维且张力 ≥ 0.70：$nht 只，其中 $nhts 只空头确立。</b>
同样九格全满，但方向朝下、波动放大——满维在这里是「跌得很有依据」。</li>
<li><b>中低确定度低张力：上港 7/9 张力 0.32、海尔 7/9 0.33、南钢 6/9 0.37。</b>
证据不全，但结构松，是「可以继续观察」的一类，不是候选。</li>
<li><b>中海油 8/9、张力 0.671、空头态 #915</b>：确定度高、方向向下、张力高，
三种坏处齐全，是今天最典型的「该躲」形态。</li>
</ul>
<div class="note warn">
<span class="k">别把这张表当买入清单</span>
九维能把「有依据」和「凭感觉」分开，不能把「会涨」和「不会涨」分开。
$nfull 只满维里，$nfs 只今天在跌——这张表如实记录了这个事实。
选股要在 L2 的四关之外再叠方向闸口，那份流程在 <a href="./pipeline.html">五层漏斗</a>。
</div>

<h2>五、行业覆盖补齐之后，结论变了什么</h2>
<p>上一版只覆盖 6 个行业、24 只样本，满维只有 4 只，答案是「银行」。补到 $nlead 个行业、
$nall 只个股之后：</p>
<ul>
<li><b>公用事业从「样本不足被拦」变成并列第一。</b>川投、国投电、长电三只满维，
不是一只孤证——这正是当初设「行业内至少 2 只」这条规则要拦的那种误判。</li>
<li><b>美容护理结构分最高（9.00）却方向 −1.00。</b>确定度和方向是两根轴，
只看其中一根都会得出相反结论。</li>
<li><b>$top_n 个行业的榜首挤在同一个索引（$top_sec）。</b>
这些板块各自只有一个形态，说明已被市场统一处理过，个股层面没有分化。</li>
</ul>

<div class="foot">
样本：$nall 只个股（覆盖 $nlead 个申万一级行业，每行业 3–9 只代表股）+ 上证 + 沪深300，
2026-10-16 至 11-20 共 26 根日 K，引擎取 21 个有效状态。行情取自新浪财经日线接口，
成交额按「成交量 × 收盘价」估算。标的清单是 <span class="mono">stock/universe.py</span> 一处。<br>
PE/PB 仅银行业 9 只有取，其余未取估值口径，故本页不再横向比较估值。<br>
本文是结构诊断，不是投资建议。向量相似不等于收益相似，历史状态不保证未来。<br>
引擎 repo：<a href="https://github.com/q1z2q3-debug/cognitive-being-v9">cognitive-being-v9</a>
　·　<a href="./index.html">返回主页</a>　·　<a href="./pipeline.html">五层漏斗</a>
　·　<a href="./bank-scan.html">同业扫描</a>　·　<a href="./chem.html">化工读数</a>
</div>
</div>
</body>
</html>
""")


if __name__ == "__main__":
    main()
