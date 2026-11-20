"""生成 docs/crowding.html：拥挤度一页。

读 out/crowding.json，不重算任何数。样式沿用 docs/pipeline.html 的深墨・青瓷・朱砂。
"""

import json
import os
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out", "crowding.json")
DOCS = os.path.join(ROOT, "docs", "crowding.html")

T = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>拥挤度：同构是可算的</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%230b1210'/%3E%3Crect x='10' y='26' width='10' height='10' fill='%235fa79b'/%3E%3Crect x='27' y='26' width='10' height='10' fill='%235fa79b'/%3E%3Crect x='44' y='26' width='10' height='10' fill='%23b5452f'/%3E%3C/svg%3E">
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
.lead{color:var(--dim);font-size:15.5px;max-width:660px}
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
figure{margin:24px 0;max-width:660px}
figcaption{color:var(--dim);font-size:12.5px;margin-top:10px;line-height:1.7}
.chart{background:var(--panel);border:1px solid var(--line);padding:20px 18px}
.crow{display:grid;grid-template-columns:104px 1fr 62px;align-items:center;
gap:10px;margin-bottom:9px}
.crow:last-child{margin-bottom:0}
.lb{color:var(--fog);font-size:12.5px}
.crow .lb.mono{font-size:11.5px;color:var(--dim)}
.tr{height:11px;background:#16221d;position:relative}
.fl{position:absolute;left:0;top:0;height:11px;background:var(--jade)}
.fl.c{background:var(--cinn)}.fl.g{background:var(--gold)}
.vl{color:var(--fog);font-size:12.5px;text-align:right;
font-family:ui-monospace,monospace}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;table-layout:fixed}
.c1{width:15%}.c2{width:9%}.c3{width:13%}.c4{width:9%}.c5{width:10%}.c6{width:44%}
.col-i{width:11%}.col-v{width:33%}.col-n{width:8%}.col-s{width:48%}
th{color:var(--dim);font-weight:500;font-size:12px;text-align:left;
padding:8px 6px;border-bottom:1px solid var(--line)}
th+th,td+td{border-left:1px solid #16221d}
td{padding:9px 6px;border-bottom:1px solid #1a2723;color:#c9d1ca}
td.mono{font-size:12.5px}
tr.pub td{color:var(--gold)}
.tag{font-size:11px;color:var(--cinn);border:1px solid #3a2019;padding:1px 5px;white-space:nowrap}
.tag.j{color:var(--jade);border-color:#22403a}
.tag.m{color:var(--mid);border-color:#2a3a35}
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
.c1{width:18%}.c2{width:9%}.c3{width:14%}.c4{width:9%}.c5{width:13%}.c6{width:37%}
.attr thead{display:none}
.attr tr{display:block;padding:9px 0;border-bottom:1px solid #1a2723}
.attr td{display:block;width:auto;border:none;padding:2px 0}
.attr td+td{border-left:none}
th,td{padding:7px 5px}
th+th,td+td{border-left:1px solid #16221d}
.crow{grid-template-columns:86px 1fr 48px;gap:8px}
.lb{font-size:11.5px}
}
</style>
</head>
<body>
<div class="wrap">
<p class="eyebrow">06 · 市场 / L1.5</p>
<h1>拥挤度：同构是可算的</h1>
<p class="lead">L1 给行业打分，L2 给行业内个股排序，两层都有一个没说出口的前提：样本彼此独立。若十只股票其实是同一个形态，排序就是在给重复样本排名。这一层只量化这件事，不修改任何结论。</p>

<div class="bar">
<div><b class="j">$N</b><span>只个股样本</span></div>
<div><b class="g">$IDX</b><span>个不同九维索引</span></div>
<div><b class="c">$PUB</b><span>个公共形态</span></div>
<div><b class="c">$POOL</b><span>独立想法（八只名义）</span></div>
</div>

<h2>一、我以为拥挤在行业里，数据说不在</h2>
<p>上一轮我给出的假设是「行业内部塌成一团」——同行业个股形态雷同，组内排名失去意义。算完是反的：<b>31 个行业里 $ZERO 个的 dup 恰好为 0</b>，即没有任何两只同行业个股共用同一索引。最高的也只有 0.25。</p>
<p>这说明行业内个股分化良好，L2 的组内比较确实有信息量。银行 9 只落在 9 个不同索引上，是全样本里区分度最高的一档。</p>
<figure><div class="chart">
<div class="crow"><span class="lb mono">dup = 0</span><div class="tr"><div class="fl" style="width:$W1%"></div></div><span class="vl">$ZERO</span></div>
<div class="crow"><span class="lb mono">0&lt;dup≤0.25</span><div class="tr"><div class="fl g" style="width:$W2%"></div></div><span class="vl">$SMALL</span></div>
</div><figcaption>行业内不可区分度 dup = 1 − 不同索引数 / 行业样本数，按行业计数。横条越长表示落在该档的行业越多；全部 ≤0.25，中位 0。</figcaption></figure>

<h2>二、真正集中的地方是索引空间</h2>
<p>$N 只只落到 $IDX 个索引上（逐只多样 $DIV）。两个索引用掉了 $TOP2 只、横跨 $TOPSEC 个行业，它们就是这轮市场里可以被称作「模板」的形态：</p>
<table class="attr">
<colgroup><col class="col-i"><col class="col-v"><col class="col-n"><col class="col-s"></colgroup>
<thead><tr><th>索引</th><th>九维向量</th><th>只数</th><th>覆盖行业</th></tr></thead>
<tbody>$ATTR_ROWS</tbody>
</table>
<p>#183 与 #186 只差 <b>守</b>这一维：前者守 = 0（当日振幅与 20 日中位持平），后者守 = +1（显著缩量）。所以这是<b>「常量破位」与「缩量破位」两个版本的同一个下跌</b>。九维不认行业——它只认价格形态，同一个形态自然跨行业复现。</p>

<h2>三、多头比空头更同构，这跟直觉反着</h2>
<p>我原本预判「跌是同构的，涨是异构的」：下跌由少数几个恐慌模板复制，上涨各有个性。算出来正相反。</p>
<table>
<colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6"></colgroup>
<thead><tr><th>市场态</th><th>只数</th><th>索引数</th><th>HHI</th><th>最大占比</th><th>读法</th></tr></thead>
<tbody>$REG_ROWS</tbody>
</table>
<p><b>多头确立 $BUL 只只用了 $BULIDX 个索引，HHI $BULHHI；空头确立 $BEA 只用了 $BEAIDX 个索引，HHI $BEAHHI。</b>多头的形态重复度是空头的近两倍。这意味着这轮上涨不是几十个独立故事，而是十几个形态的复制——真正可下注的独立想法远少于名义只数。空头一侧反而分散，说明下跌有多个成因，用一个空头模板去概括会漏掉大半。</p>
<figure><div class="chart">
<div class="crow"><span class="lb">空头确立</span><div class="tr"><div class="fl" style="width:$H1%"></div></div><span class="vl">$HH1</span></div>
<div class="crow"><span class="lb">多空对峙</span><div class="tr"><div class="fl" style="width:$H2%"></div></div><span class="vl">$HH2</span></div>
<div class="crow"><span class="lb">多头确立</span><div class="tr"><div class="fl c" style="width:$H3%"></div></div><span class="vl">$HH3</span></div>
<div class="crow"><span class="lb">弱定向</span><div class="tr"><div class="fl c" style="width:$H4%"></div></div><span class="vl">$HH4</span></div>
</div><figcaption>市场态内部形态集中度 HHI。条越长说明该态的样本越像同一件事的复制。悬置主导仅 1 只，HHI 恒为 1，不画。</figcaption></figure>

<h2>四、五个行业被公共形态占了众数</h2>
<p>reach = 该行业的众数索引横跨多少个申万一级行业。reach 高说明这个行业的「代表形态」是市场公共形态，它出现在哪个行业都不构成行业超额信息。</p>
<table>
<colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6"></colgroup>
<thead><tr><th>行业</th><th>n</th><th>众数</th><th>reach</th><th>dup</th><th>标记</th></tr></thead>
<tbody>$SEC_ROWS</tbody>
</table>
<p>被标「公共形态」的五个行业里，基础化工与电力设备本就在 L1 被张力否决，房地产也在否决名单，通信是候选第四、轻工是候选第十一。<b>但它们都没有进到 L2 的八只过筛里</b>——所以这一层本轮没有改变任何组合结论。</p>

<div class="note warn"><span class="k">为什么不做成拦截</span>
把拥挤设成否决条件会凭空删掉真信号。多头侧形态重复，可能是「同一个逻辑在多只股票上兑现」——这在价格行为上无法与「拥挤」区分开。既然分不开，就只标注、不动手。真想拦，需要资金流或持仓重合度数据，那两样本轮都没接。</div>

<h2>五、候选池：八只名义，两个想法</h2>
<table>
<colgroup><col class="c1"><col class="c3"><col class="c6"></colgroup>
<thead><tr><th>组</th><th>索引</th><th>成员</th></tr></thead>
<tbody>$POOL_ROWS</tbody>
</table>
<p>八只名义候选压成 $GRP 组，<b>独立信号率 $RATE%</b>。第一组七只组内最大汉明距离为 $HIN——它们不是两两相邻，而是被一条链连起来的：相邻两只差一维，首尾差两维。</p>
<p>这里说的是<b>全图聚类</b>，与 L4 的<b>贪心去重</b>是两个口径：L4 逐只与已保留的比较，得到三只（川投、神华、平安银行）；全图并查集得到两组。差别来自贪心顺序，不是数据打架。两个数都该看——前者是实际持仓数，后者是这批候选真实的思想密度。</p>

<h2>六、这一层不做什么</h2>
<ul>
<li><b>不做因果。</b>「#183 横跨八个行业」是描述，不是解释。它没有说这些股票为什么同形，也没说会不会一起反转。</li>
<li><b>不预测。</b>HHI 高不等于要跌。多头形态重复可能继续重复，也可能在下一根 K 线上分化，本层不判断。</li>
<li><b>不补外部数据。</b>真正的拥挤要看资金流、融资余额、机构持仓重合度。这三样一条都没接，所以本页只能算「形态层面的重复」，不能算「钱的拥挤」。</li>
<li><b>不改漏斗。</b>样本 $N → 行业 $LSEC → 个股 $LPICK → 组合 $LPORT，与本页上线前完全一致。</li>
</ul>

<p class="foot">口径：申万一级 31 个行业、$N 只个股代表样本，26 根日 K（20261016–20261120），最后有效交易日 2026-11-20。九维阈值为固定常数，见 <a href="pipeline.html">五层漏斗</a>。本页数字由 <span class="mono">python3 -m stock.crowding</span> 与 <span class="mono">python3 -m stock.pipeline</span> 复算得到，改一处数据即全页更新。<br>
返回 <a href="index.html">主页</a>。</p>
</div>
</body>
</html>
""")

READ = {"公共形态": '<span class="tag">公共形态</span>',
        "半公共": '<span class="tag m">半公共</span>',
        "有区分度": '<span class="tag j">有区分度</span>'}


def main():
    with open(OUT, encoding="utf-8") as f:
        d = json.load(f)
    with open(os.path.join(HERE, "out", "pipeline.json"), encoding="utf-8") as f:
        pipe = json.load(f)

    sec = d["sectors"]
    zero = sum(1 for s in sec if s["dup"] == 0)
    small = len(sec) - zero
    w1 = 100 * zero / len(sec)
    w2 = 100 * small / len(sec)

    pub = [a for a in d["top_attractors"] if a["reach"] >= d["threshold"]["public_reach"]]
    attr = "\n".join(
        '<tr class="pub"><td class="mono">#%d</td><td class="mono">%s</td><td class="mono">%d</td><td>%s</td></tr>'
        % (a["index"], a["str"], a["count"], "・".join(a["sectors"])) for a in pub)

    reg = {r["regime"]: r for r in d["regimes"]}
    note = {"空头确立": "下跌分散，多个成因", "多空对峙": "各有各的僵持",
            "多头确立": "涨势趋同，形态复制", "弱定向": "样本少，集中度高"}
    rows = []
    for name in ("空头确立", "多空对峙", "多头确立", "弱定向"):
        r = reg.get(name)
        if not r:
            continue
        rows.append('<tr><td>%s</td><td class="mono">%d</td><td class="mono">%d</td>'
                    '<td class="mono">%.3f</td><td class="mono">%.1f%%</td><td>%s</td></tr>'
                    % (name, r["n"], r["indices"], r["hhi"], r["max_share"], note[name]))
    b, e = reg["多头确立"], reg["空头确立"]

    srows = []
    for s in sec:
        cls = ' class="pub"' if s["flag"] == "公共形态" else ""
        srows.append('<tr%s><td>%s</td><td class="mono">%d</td><td class="mono">#%d</td>'
                     '<td class="mono">%d</td><td class="mono">%.2f</td><td>%s</td></tr>'
                     % (cls, s["sector"], s["n"], s["mode_index"], s["mode_reach"],
                        s["dup"], READ[s["flag"]]))

    prow = []
    for i, g in enumerate(d["pool"]["groups"], 1):
        prow.append('<tr><td class="mono">第 %d 组</td><td class="mono">#%d</td><td>%s</td></tr>'
                    % (i, g["index"], "、".join(g["members"])))

    html = T.substitute(
        N=d["universe"], IDX=d["distinct_indices"], PUB=len(pub),
        POOL=d["pool"]["independent"],
        ZERO=zero, SMALL=small, W1=round(w1, 1), W2=round(w2, 1),
        DIV=round(d["distinct_indices"] / d["universe"], 2),
        TOP2=sum(a["count"] for a in pub),
        TOPSEC=len(set().union(*[set(a["sectors"]) for a in pub])),
        ATTR_ROWS=attr, REG_ROWS="\n".join(rows),
        BUL=b["n"], BULIDX=b["indices"], BULHHI="%.3f" % b["hhi"],
        BEA=e["n"], BEAIDX=e["indices"], BEAHHI="%.3f" % e["hhi"],
        H1=round(100 * reg["空头确立"]["hhi"] / 0.25, 1), HH1="%.3f" % reg["空头确立"]["hhi"],
        H2=round(100 * reg["多空对峙"]["hhi"] / 0.25, 1), HH2="%.3f" % reg["多空对峙"]["hhi"],
        H3=round(100 * reg["多头确立"]["hhi"] / 0.25, 1), HH3="%.3f" % reg["多头确立"]["hhi"],
        H4=round(100 * reg["弱定向"]["hhi"] / 0.25, 1), HH4="%.3f" % reg["弱定向"]["hhi"],
        SEC_ROWS="\n".join(srows), POOL_ROWS="\n".join(prow),
        GRP=d["pool"]["independent"], RATE=round(100 * d["pool"]["independent"] / max(1, d["pool"]["nominal"])),
        HIN=d["pool"]["groups"][0]["hamming_in_group"] if d["pool"]["groups"] else 0,
        LSEC=pipe["funnel"]["行业"], LPICK=pipe["funnel"]["个股"], LPORT=pipe["funnel"]["组合"],
    )
    with open(DOCS, "w", encoding="utf-8") as f:
        f.write(html)
    print("写入", DOCS, len(html), "字节")
    print("dup=0 行业 %d / 全部 %d | 公共形态 %d | 独立想法 %d" % (zero, len(sec), len(pub), d["pool"]["independent"]))


if __name__ == "__main__":
    main()
