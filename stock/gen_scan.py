"""银行同业扫描：以平安为基准，算九维汉明距离，出一页邻居谱系。

只读 stock/out/stock_state.json（由 run.py 全量扫描生成），不重跑引擎。
输出：
  stock/scan_report.html        —— 工程内留档
  ../docs/bank-scan.html        —— 线上同步
  stock/out/scan.svg            —— 状态矩阵热图

判据（"待爆发"）：
  正=+1 且 合=+1（方向已立）  +  进=0（动量未起）  +  归≠-1（未到区间顶）
三者同时成立才算命中。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from cognitive_being.ternary_algebra import hamming_distance  # noqa: E402

DIMS = ["天", "地", "人", "正", "反", "合", "归", "守", "进"]

# 估值（2026-11-20 收盘，与行情表同源）
VAL = {
    "平安银行 000001.SZ": (5.4540, 0.4975),
    "北京银行 601169.SH": (6.2031, 0.4553),
    "浦发银行 600000.SH": (6.9931, 0.4768),
    "华夏银行 600015.SH": (4.4837, 0.3309),
    "光大银行 601818.SH": (6.3841, 0.3727),
    "兴业银行 601166.SH": (5.7222, 0.5049),
    "民生银行 600016.SH": (5.7670, 0.2644),
    "沪深300 000300": (0, 0),
    "上证指数 000001": (0, 0),
}
SHORT = {
    "平安银行 000001.SZ": "平安",
    "北京银行 601169.SH": "北京",
    "浦发银行 600000.SH": "浦发",
    "华夏银行 600015.SH": "华夏",
    "光大银行 601818.SH": "光大",
    "兴业银行 601166.SH": "兴业",
    "民生银行 600016.SH": "民生",
    "沪深300 000300": "沪深300",
    "上证指数 000001": "上证",
    "招商银行 600036.SH": "招商",
    "工商银行 601398.SH": "工商",
}
BASE = "平安银行 000001.SZ"


# 本页只扫银行池 + 两大指数。stock_state.json 是全市场样本，
# 不过滤的话化工等新样本会混进来，"九只银行"的口径就不成立了。
from stock.universe import UNIVERSE, INDEX   # noqa: E402

TARGETS = (INDEX[0].label, INDEX[1].label,
           "平安银行 000001.SZ", "浦发银行 600000.SH", "华夏银行 600015.SH",
           "民生银行 600016.SH", "招商银行 600036.SH", "兴业银行 601166.SH",
           "北京银行 601169.SH", "工商银行 601398.SH", "光大银行 601818.SH")


def load():
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    base_state = None
    for name, v in raw.items():
        if name not in TARGETS:
            continue
        last = [x for x in v["series"] if x["valid"]][-1]
        rows.append({
            "name": name,
            "short": SHORT.get(name, name),
            "state": last["state"],
            "index": last["index"],
            "regime": last["regime"],
            "tension": last["tension"]["T"],
            "certain": sum(1 for q in last["obs"] if q),
            "suspend": sum(1 for q in last["obs"] if not q),
            "nonzero": sum(1 for q in last["state"] if q),
            "pe": VAL.get(name, (0, 0))[0],
            "pb": VAL.get(name, (0, 0))[1],
        })
        if name == BASE:
            base_state = last["state"]
    for r in rows:
        r["dist"] = hamming_distance(r["state"], base_state)
        a, b, c, d = r["state"][3], r["state"][5], r["state"][8], r["state"][6]
        r["dormant"] = (a == 1 and b == 1 and c == 0 and d != -1)
    rows.sort(key=lambda r: (r["dist"], -r["certain"]))
    return rows, base_state


def cell_class(v):
    if v == 1:
        return "pos"
    if v == -1:
        return "neg"
    return "neu"


def make_svg(rows):
    w, h = 380, 348
    top = 44
    rh = 25
    x0 = 80
    cw, gap = 22.5, 3
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'role="img" aria-label="九维状态矩阵：九只银行股与大盘指数，按与平安银行的汉明距离排序">' % (w, h),
        "<style>"
        "text{font-family:'Songti SC','Noto Serif CJK SC',serif}"
        ".pos{fill:#5fa79b}.neg{fill:#b5452f}.neu{fill:#3a4a44}"
        ".tl{fill:#e8e2d5;font-size:11px}"
        ".hd{fill:#87968f;font-size:9.5px}"
        ".dt{fill:#c8a45c;font-size:10px}"
        ".mt{fill:#87968f;font-size:9px}"
        "</style>",
        '<rect x="0" y="0" width="%d" height="%d" fill="#0f1a16"/>' % (w, h),
        '<text x="18" y="16" class="tl">与平安的汉明距离（九维，由近及远）</text>',
    ]
    for i, d in enumerate(DIMS):
        parts.append('<text x="%g" y="34" class="hd" text-anchor="middle">%s</text>'
                     % (x0 + i * (cw + gap) + cw / 2, d))
    parts.append('<text x="372" y="34" class="hd" text-anchor="end">距</text>')
    for r, row in enumerate(rows):
        y = top + r * rh
        is_base = row["dist"] == 0
        if is_base:
            parts.append('<rect x="4" y="%g" width="368" height="%g" fill="#5fa79b" opacity=".10"/>'
                         % (y, rh - 3))
        color = "#e8e2d5" if is_base else "#b9c2bc"
        parts.append('<text x="8" y="%g" class="mt" fill="%s">%s</text>'
                     % (y + rh / 2 + 3.5, color, row["short"]))
        for i, v in enumerate(row["state"]):
            cx = x0 + i * (cw + gap)
            parts.append('<rect x="%g" y="%g" width="%g" height="18" rx="2" class="%s" '
                         'opacity="%s"/>' % (cx, y, cw, cell_class(v),
                                             ".95" if v else ".30"))
            if v:
                parts.append('<text x="%g" y="%g" font-size="8" fill="#0b1210" '
                             'text-anchor="middle" font-family="monospace">%s</text>'
                             % (cx + cw / 2, y + 12.5, "+" if v == 1 else "−"))
        dtxt = "0" if row["dist"] == 0 else ("−%d" % row["dist"])
        parts.append('<text x="372" y="%g" class="dt" text-anchor="end">%s</text>'
                     % (y + rh / 2 + 3.5, dtxt))
    parts.append('<text x="8" y="%g" class="hd">青 = +1 成立　朱 = −1 反证　暗 = 0 悬置</text>'
                 % (top + len(rows) * rh + 14))
    parts.append('<text x="8" y="%g" class="hd">距 1 的两只只差一维：北京差「守」，浦发差「人」</text>'
                 % (top + len(rows) * rh + 28))
    parts.append("</svg>")
    return "\n".join(parts)


def make_html(rows, base_state):
    n1 = sum(1 for r in rows if r["dist"] == 1)
    n3 = sum(1 for r in rows if 0 < r["dist"] <= 3)
    hit = [r for r in rows if r["dormant"]]

    trs = []
    for r in rows:
        hl = ' class="hl"' if r["dist"] <= 1 else ""
        pe = "%.2f" % r["pe"] if r["pe"] else "—"
        pb = "%.3f" % r["pb"] if r["pb"] else "—"
        rows_html = (
            "<tr%s><td>%s</td><td class=\"mono\">%d</td><td class=\"mono\">#%d</td>"
            "<td>%s</td><td class=\"mono\">%.2f</td><td class=\"mono\">%d/9</td>"
            "<td class=\"mono\">%s</td><td class=\"mono\">%s</td></tr>"
            % (hl, r["short"], r["dist"], r["index"], r["regime"], r["tension"],
               r["certain"], pe, pb)
        )
        trs.append(rows_html)

    if hit:
        verdict = "命中 %d 只：%s。" % (len(hit), "、".join(r["short"] for r in hit))
    else:
        verdict = ("九只全部未命中。原因不是它们不好，而是它们都已经走过了——"
                   "归维一律 −1（落在 20 日区间上沿），离零 7–8 层（空间重心是 6）。"
                   "这个池子已经结晶，没有「未定」的余地。")

    svg = make_svg(rows)
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>平安的两个邻居 · 银行同业九维扫描</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%%3E%%3Crect width='64' height='64' fill='%%230b1210'/%%3E%%3Crect x='8' y='8' width='14' height='14' fill='%%235fa79b'/%%3E%%3Crect x='25' y='8' width='14' height='14' fill='%%235fa79b'/%%3E%%3Crect x='42' y='8' width='14' height='14' fill='%%233a4a44'/%%3E%%3Crect x='8' y='25' width='14' height='14' fill='%%235fa79b'/%%3E%%3Crect x='25' y='25' width='14' height='14' fill='%%23b5452f'/%%3E%%3Crect x='42' y='25' width='14' height='14' fill='%%235fa79b'/%%3E%%3Crect x='8' y='42' width='14' height='14' fill='%%23b5452f'/%%3E%%3Crect x='25' y='42' width='14' height='14' fill='%%233a4a44'/%%3E%%3Crect x='42' y='42' width='14' height='14' fill='%%235fa79b'/%%3E%%3C/svg%%3E">
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
h1{font-size:34px;line-height:1.25;font-weight:600;margin:14px 0 10px;letter-spacing:.02em}
.lead{color:var(--dim);font-size:15.5px;max-width:620px}
.hr{height:1px;background:var(--line);margin:38px 0}
.bar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);
border:1px solid var(--line);margin:32px 0}
.bar div{background:var(--panel);padding:16px 14px}
.bar b{display:block;font-size:26px;line-height:1.2;color:var(--fog);
font-family:ui-monospace,monospace;font-variant-numeric:tabular-nums}
.bar span{display:block;color:var(--dim);font-size:12px;margin-top:4px;letter-spacing:.06em}
.bar b.j{color:var(--jade)}.bar b.g{color:var(--gold)}.bar b.c{color:var(--cinn)}
h2{font-size:19px;font-weight:600;margin:40px 0 14px;color:var(--fog)}
h2::before{content:"";display:inline-block;width:3px;height:15px;background:var(--gold);
vertical-align:-2px;margin-right:10px}
p{margin:0 0 14px;color:#cfd6cf}
figure{margin:26px 0;max-width:640px}
figure svg{width:100%%;height:auto;display:block;border:1px solid var(--line)}
figcaption{color:var(--dim);font-size:12.5px;margin-top:10px;line-height:1.7}
table{width:100%%;border-collapse:collapse;margin:18px 0;font-size:14px;table-layout:fixed}
th{color:var(--dim);font-weight:500;font-size:12px;letter-spacing:.08em;
text-align:left;padding:8px 6px;border-bottom:1px solid var(--line)}
td{padding:9px 6px;border-bottom:1px solid #1a2723;color:#c9d1ca}
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

table{font-size:12.5px}th{font-size:11px}th,td{padding:7px 4px}
}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">润泽说 · 认知生命体 v9 · 引擎读数</div>
<h1>平安的两个邻居</h1>
<p class="lead">把九只银行股和两个指数丢进同一套九维编码器，"像不像平安"就不再是感觉，
而是一个整数——两个状态向量之间改了几个位置。结果比预想的窄得多。</p>

<div class="bar">
<div><b>9</b><span>同业样本</span></div>
<div><b class="g">%d</b><span>距平安 1 维</span></div>
<div><b class="j">%d</b><span>距 ≤3 维</span></div>
<div><b class="c">%d</b><span>待爆发命中</span></div>
</div>

<figure>
%s
<figcaption>按与平安的汉明距离排序。青为 +1（成立）、朱为 −1（反证）、暗为 0（悬置）。
第一行是平安本身，最后两行是大盘。</figcaption>
</figure>

<h2>一、最近的两个，各差一维</h2>
<p><b>北京银行 #18767</b> 与平安只差「守」：平安守 = 0（振幅正常），北京守 = −1（当日振幅 1.8 倍于常态）。
其余八维完全一致——天 +1、地 +1、正 +1、反 −1、合 +1、归 −1、进 +1。</p>
<p><b>浦发银行 #19499</b> 与平安只差「人」：浦发人 = +1（近三日收益 +1%% 已过阈值），
平安人 = 0（差一点点）。这一维之差，就是"有没有启动"的分界。</p>
<p>所以答案不是"下一个平安在哪"，而是：平安的结构在这个池子里有 <b>且仅有两个</b> 近邻，
一个差在波动，一个差在动能。</p>

<h2>二、浦发已完成启动，北京是同构但更躁</h2>
<p>浦发是九只中除平安外<b>唯一判为「多头确立」</b>的：6/9 确定、张力 0.40、进维 +1（5 日 +4.52%%）、
成交额 1.18 倍均额、PB 0.4768 与平安 0.4975 同档。它的引擎读数比平安还完整一维。</p>
<p>北京银行则相反：状态同构，但守维 −1 说明它在 11/20 那根 K 上振幅放大了 1.8 倍——
11/20 收 6.27、涨 1.13%%、成交 16.55 亿（1.3 倍均额），振幅 6.13–6.28。
同样的方向，更急的步子。它的 PB 只有 0.4553，是九只里最低的一档。</p>

<div class="note">
<span class="k">引擎的判词</span>
浦发 = 平安 + 动能；北京 = 平安 + 波动。两者都是"已经动了"，不是"要动"。
</div>

<h2>三、没有"待爆发"的——这个池子已经结晶</h2>
<p>把"待爆发"写成可计算的条件：<b>正 = +1 且 合 = +1</b>（方向已立）+
<b>进 = 0</b>（动量未起）+ <b>归 ≠ −1</b>（还没到区间顶）。三条同时成立才算。</p>
<p>%s</p>
<p>再看零元视角：九只离零态（全悬置 #9841）的距离全部落在 <b>7–9 层</b>，
而 19683 态空间的重心在 <b>6 层</b>（5376 个态，27.3%%）。没有一只回到重心附近。</p>
<div class="note warn">
<span class="k">这条比选股更值钱</span>
引擎说的不是"哪只票会涨"，而是"这个板块已经没有未定的余地了"。
当所有标的都站在区间上沿、都离零 7 层以上，剩下的只有分化，没有发现。
要找"待爆发"，得换池子——而不是在同一批已经涨过的银行里再挑一遍。
</div>

<h2>四、九维读数对照</h2>
<table>
<colgroup>
<col style="width:13%%"><col style="width:12%%"><col style="width:14%%"><col style="width:19%%">
<col style="width:10%%"><col style="width:9%%"><col style="width:12%%"><col style="width:11%%">
</colgroup>
<thead><tr><th>标的</th><th>距</th><th>索引</th><th>市场态</th><th>张力</th>
<th>确定</th><th>PE</th><th>PB</th></tr></thead>
<tbody>
%s
</tbody>
</table>
<p style="color:#87968f;font-size:13px">「确定」= 九维中有明确值的维度数，其余为悬置。
距离越小越像，确定越多越有方向，张力越高越吃紧。</p>

<h2>五、要继续找，该往哪儿看</h2>
<ul>
<li><b>换池子。</b>银行已经走完一轮；同构的未结晶标的更可能在非银、券商、保险、
以及地产链里——它们的估值修复往往滞后银行一个季度。</li>
<li><b>用条件筛，不用感觉筛。</b>天/合转正、进仍为 0、归不在 −1、张力 &lt; 0.45、离零 ≤6 层。
五条全中，才是引擎意义上的"待爆发"。</li>
<li><b>别把距离小当成涨幅小。</b>距离只说明结构像，不说明空间大。
北京距平安 1 维，但它今天的振幅已经是平安的 1.8 倍。</li>
</ul>

<div class="foot">
样本：9 只（7 只银行 + 上证 + 沪深300），2026-10-16 至 11-20 共 26 根日 K，引擎取 21 个有效状态。<br>
编码器为固定阈值的九维规则编码（天=MA20 偏离 ±0.5%%、地=量比 1.15/0.85、人=近 3 日 ±1%%、
正=MA5 抬升、反=创 10 日新高/低、合=均线同向、归=20 日区间分位 0.2/0.8、守=振幅 0.8/1.25、
进=5 日动量 ±1.5%%），不含任何基本面与消息面输入。<br>
距离口径：本文用汉明距离。它把「+1 对 −1」的翻转与「有值对悬置」的缺失
同等记作 1，中段排序会与欧式分歧（华夏 vs 工商即为反例），
详见<a href="./chem.html">化工页第四节</a>。<br>
本文是结构诊断，不是投资建议。向量相似不等于收益相似，历史状态不保证未来。<br>
引擎 repo：<a href="https://github.com/q1z2q3-debug/cognitive-being-v9">cognitive-being-v9</a>
　·　<a href="./index.html">返回主页</a>　·　<a href="./pa-000001.html">平安个股页</a>　·　<a href="./stock-indices.html">指数页</a>
</div>
</div>
</body>
</html>
""" % (n1, n3, len(hit), svg, verdict, "\n".join(trs))


def main():
    rows, base_state = load()
    html = make_html(rows, base_state)
    out_svg = os.path.join(HERE, "out", "scan.svg")
    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(make_svg(rows))
    for path in (os.path.join(HERE, "scan_report.html"),
                 os.path.join(os.path.dirname(HERE), "docs", "bank-scan.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("wrote", path)
    print("hit:", [r["short"] for r in rows if r["dormant"]])
    for r in rows:
        print("%-6s dist=%d nz=%d idx=%d %s t=%.2f %d/9 dormant=%s"
              % (r["short"], r["dist"], r["nonzero"], r["index"], r["regime"],
                 r["tension"], r["certain"], r["dormant"]))


if __name__ == "__main__":
    main()
