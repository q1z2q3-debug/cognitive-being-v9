"""跨行业维度评分：18 个标的的九维确定度排序。

输入 stock/out/stock_state.json（run.py 全量扫描产出），只读不重跑。
输出 stock/rank_report.html、docs/rank.html、stock/out/rank.svg
"""
import json
import os
import sys
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

SECTOR = {
    "上证指数 000001": "指数",
    "沪深300 000300": "指数",
    "平安银行 000001.SZ": "银行",
    "浦发银行 600000.SH": "银行",
    "华夏银行 600015.SH": "银行",
    "民生银行 600016.SH": "银行",
    "招商银行 600036.SH": "银行",
    "兴业银行 601166.SH": "银行",
    "北京银行 601169.SH": "银行",
    "工商银行 601398.SH": "银行",
    "光大银行 601818.SH": "银行",
    "中国神华 601088.SH": "煤炭",
    "陕西煤业 601225.SH": "煤炭",
    "中国石油 601857.SH": "石油石化",
    "中国海油 600938.SH": "石油石化",
    "长江电力 600900.SH": "公用事业",
    "中国人寿 601628.SH": "保险",
    "中国平安 601318.SH": "保险",
}
SHORT = {
    "上证指数 000001": "上证",
    "沪深300 000300": "沪深300",
    "平安银行 000001.SZ": "平安银行",
    "浦发银行 600000.SH": "浦发",
    "华夏银行 600015.SH": "华夏",
    "民生银行 600016.SH": "民生",
    "招商银行 600036.SH": "招商",
    "兴业银行 601166.SH": "兴业",
    "北京银行 601169.SH": "北京",
    "工商银行 601398.SH": "工商",
    "光大银行 601818.SH": "光大",
    "中国神华 601088.SH": "神华",
    "陕西煤业 601225.SH": "陕煤",
    "中国石油 601857.SH": "中石油",
    "中国海油 600938.SH": "中海油",
    "长江电力 600900.SH": "长电",
    "中国人寿 601628.SH": "人寿",
    "中国平安 601318.SH": "中国平安",
}
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
        rows.append({
            "name": name,
            "short": SHORT.get(name, name),
            "sector": SECTOR.get(name, "—"),
            "state": last["state"],
            "index": last["index"],
            "regime": last["regime"],
            "tension": last["tension"]["T"],
            "certain": sum(1 for q in last["obs"] if q),
            "suspend": sum(1 for q in last["obs"] if not q),
        })
    rows.sort(key=lambda r: (-r["certain"], r["tension"], r["short"]))
    return rows


def tone(regime):
    if "多头" in regime:
        return "pos"
    if "空头" in regime:
        return "neg"
    return "neu"


def make_svg(rows):
    w = 380
    top = 46
    rh = 19
    h = top + len(rows) * rh + 34
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" '
        'aria-label="18 个标的的九维确定度排序，按维度填满程度由高到低">' % (w, h),
        "<style>"
        ".tl{fill:#e8e2d5;font-size:10.5px}"
        ".hd{fill:#87968f;font-size:9px}"
        ".nm{fill:#c9d1ca;font-size:9.5px}"
        ".tg{fill:#87968f;font-size:9px}"
        ".pos{fill:#5fa79b}.neg{fill:#b5452f}.neu{fill:#6b7a74}"
        "</style>",
        '<rect width="%d" height="%d" fill="#0f1a16"/>' % (w, h),
        '<text x="10" y="18" class="tl">九维确定度（填满 9 格 = 每一维都有依据）</text>',
        '<text x="78" y="34" class="hd">1</text>',
        '<text x="272" y="34" class="hd" text-anchor="end">9</text>',
        '<text x="316" y="34" class="hd" text-anchor="end">张力</text>',
        '<text x="372" y="34" class="hd" text-anchor="end">态</text>',
    ]
    x0 = 78
    cw, gap = 20, 2
    for r, row in enumerate(rows):
        y = top + r * rh
        full = row["certain"] == 9
        if full:
            parts.append('<rect x="4" y="%g" width="372" height="%g" fill="#5fa79b" opacity=".09"/>'
                         % (y, rh - 2))
        col = "#e8e2d5" if full else "#b9c2bc"
        parts.append('<text x="8" y="%g" class="nm" fill="%s">%s</text>'
                     % (y + 12, col, row["short"]))
        for i in range(9):
            cx = x0 + i * (cw + gap)
            fill = "class=\"%s\" opacity=\".85\"" % tone(row["regime"]) if i < row["certain"] else \
                   'fill="#1b2723"'
            parts.append('<rect x="%g" y="%g" width="%g" height="12" rx="1.5" %s/>'
                         % (cx, y + 2, cw, fill))
        parts.append('<text x="316" y="%g" class="tg" text-anchor="end">%.2f</text>'
                     % (y + 12, row["tension"]))
        tag = "多头" if "多头" in row["regime"] else ("空头" if "空头" in row["regime"] else
                                                    ("弱定" if "弱" in row["regime"] else "对峙"))
        parts.append('<text x="372" y="%g" class="tg" text-anchor="end">%s</text>'
                     % (y + 12, tag))
    parts.append('<text x="10" y="%g" class="hd">青 = 多头确立　灰 = 多空对峙　朱 = 空头确立</text>'
                 % (top + len(rows) * rh + 16))
    parts.append('<text x="10" y="%g" class="hd">高亮行为九维全满（0 悬置），共 4 只</text>'
                 % (top + len(rows) * rh + 30))
    parts.append("</svg>")
    return "\n".join(parts)


def make_html(rows):
    full = [r for r in rows if r["certain"] == 9]
    trs = []
    for r in rows:
        hl = ' class="hl"' if r["certain"] == 9 else ""
        pe, pb = VOL15.get(r["name"], (0, 0))
        trs.append(
            "<tr%s><td>%s</td><td>%s</td><td class=\"mono\">#%d</td><td>%s</td>"
            "<td class=\"mono\">%d/9</td><td class=\"mono\">%.2f</td><td class=\"mono\">%s</td></tr>"
            % (hl, r["short"], r["sector"], r["index"], r["regime"], r["certain"],
               r["tension"], ("%.2f" % pe) if pe else "—"))
    body = "\n".join(trs)
    return TEMPLATE.substitute(
        n=len(rows), nfull=len(full), svg=make_svg(rows), rows=body,
        full_names="、".join(r["short"] for r in full))


TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>维度最佳的四只 · 跨行业九维评分</title>
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
.lead{color:var(--dim);font-size:15.5px;max-width:640px}
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
col{width:auto}
th{color:var(--dim);font-weight:500;font-size:12px;text-align:left;
padding:8px 6px;border-bottom:1px solid var(--line)}
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
<h1>维度最佳的四只</h1>
<p class="lead">把 18 个标的——9 只银行、2 只保险、2 只煤炭、2 只石油石化、1 只公用事业，加两大指数——
塞进同一把九维尺子。不看行业，只看谁能把九个格子全部填满。</p>

<div class="bar">
<div><b>$n</b><span>跨行业标的</span></div>
<div><b class="j">$nfull</b><span>九维全满</span></div>
<div><b class="g">+1.29%</b><span>银行今日涨幅</span></div>
<div><b class="c">27</b><span>下跌行业数</span></div>
</div>

<figure>
$svg
<figcaption>按九维确定度降序。格数即「观测层有明确值的维度数」，剩余为悬置。
高亮行是 0 悬置的满维标的。</figcaption>
</figure>

<h2>一、行业：今天只有四条线站得住</h2>
<p>11 月 20 日，申万 31 个一级行业里只有 <b>4 个收红</b>：银行 +1.29%、煤炭 +0.33%、
石油石化 +0.31%、公用事业 +0.02%。剩下 27 个全线下跌，综合 −5.92%、机械设备 −4.77%、
电子 −4.60%、国防军工 −4.54%、计算机 −4.69%。</p>
<p>同日上证 −1.22%、深成指 −3.09%、创业板指 −3.54%，超 5200 只个股下跌。
资金没有选择余地，只能往这四条线上躲——这就是「维度最佳行业」的答案：
<b>银行</b>，且不是勉强翻红，是唯一有幅度的。</p>

<h2>二、个股：三只落在同一个索引</h2>
<p>招商银行、长江电力、中国平安（保险）——三只标的的九维累积态<b>完全相同</b>：
<span class="mono">[1,0,1,1,-1,1,-1,0,1]</span>，索引全是 <b>#17312</b>，观测层 0 维悬置。</p>
<p>再加工商银行 <b>#17311</b>（只差「进」维未落），共 <b>$nfull</b> 只把九维填满：
$full_names。</p>

<div class="note">
<span class="k">这条比名单重要</span>
银行、保险、公用事业三个不相干的行业，可以落进同一个状态。
九维不认行业，只认形态——所以「维度最佳」问的不是哪个行业好，
而是谁的每一个判断都有证据。
</div>

<h2>三、18 个标的的九维读数</h2>
<table>
<thead><tr><th>标的</th><th>行业</th><th>索引</th><th>市场态</th><th>确定</th><th>张力</th><th>PE</th></tr></thead>
<tbody>
$rows
</tbody>
</table>
<p style="color:#87968f;font-size:13px">PE 仅列银行业（其余未取估值口径，不作横向比较）。
确定 = 观测层有值的维度数；张力 = 0.4 波动负荷 + 0.3 跌破 MA20 深度 + 0.3 状态抖动。</p>

<h2>四、满维不等于安全</h2>
<ul>
<li><b>三只满维的张力都在 0.467–0.50。</b>填满九格的意思是「每一维都有依据」，
不是「没有风险」。张力过 0.45 说明波动负荷或跌破深度已经在咬。</li>
<li><b>中国海油 8/9 却落在空头结构 #915、张力 0.671</b>：确定度高，方向向下，
这是最该躲的一种形态——维度和方向是两件事。</li>
<li><b>陕西煤业张力 0.363，全场最低</b>，但只有 5/9：判断轻，因为证据少。</li>
<li><b>中国石油 #8527</b>：六维确定，但地、合两维为 −1，处在量价背离里。</li>
</ul>
<div class="note warn">
<span class="k">别把这张表当买入清单</span>
九维衡量的是「价格行为被证据覆盖的程度」。
它能把「有依据」和「凭感觉」分开，不能把「会涨」和「不会涨」分开。
四只满维标的今天全部上涨，明天是否延续，这张表不负责回答。
</div>

<h2>五、如果要往下走</h2>
<ul>
<li><b>银行内部再分层</b>：招商 9/9 满维、兴业 8/9、浦发 6/9 多头、北京 5/9 同构平安。
同一条线里，确定度从 9 掉到 5，就是「共识厚度」的差别。</li>
<li><b>盯张力而不是盯涨幅</b>：中海油 0.671、上证 0.699 是两个警报位；
满维三只都在 0.5 附近，随时会掉维。</li>
<li><b>煤炭是唯一「低张力 + 有方向」的组合</b>：陕煤 0.363 多头、神华 8/9 对峙。
今天只涨 0.33%，但结构比银行松。</li>
</ul>

<div class="foot">
样本：18 个标的（9 银行 + 2 保险 + 2 煤炭 + 2 石油石化 + 1 公用事业 + 上证 + 沪深300），
2026-10-16 至 11-20 共 26 根日 K，引擎取 21 个有效状态。新增标的行情取自新浪财经日线接口，
成交额按「成交量 × 收盘价」估算，量比口径与真实成交额一致，绝对额仅供参照。<br>
行业涨幅引自 2026-11-20 收盘的申万一级行业口径（粤开市场日报／新浪财经收盘稿）。<br>
本文是结构诊断，不是投资建议。向量相似不等于收益相似，历史状态不保证未来。<br>
引擎 repo：<a href="https://github.com/q1z2q3-debug/cognitive-being-v9">cognitive-being-v9</a>
　·　<a href="./index.html">返回主页</a>　·　<a href="./bank-scan.html">同业扫描</a>
　·　<a href="./pa-000001.html">平安个股</a>
</div>
</div>
</body>
</html>
""")


def main():
    rows = load()
    out_svg = os.path.join(HERE, "out", "rank.svg")
    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(make_svg(rows))
    html = make_html(rows)
    for path in (os.path.join(HERE, "rank_report.html"),
                 os.path.join(os.path.dirname(HERE), "docs", "rank.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("wrote", path)
    for r in rows:
        print("%-8s %-6s %d/9 %.3f %s #%d" % (r["short"], r["sector"], r["certain"],
                                             r["tension"], r["regime"], r["index"]))


if __name__ == "__main__":
    main()
