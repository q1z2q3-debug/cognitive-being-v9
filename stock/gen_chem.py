"""化工专项：8 只化工标的的九维读数，与银行多头结构对照。

读 stock/out/stock_state.json（run.py 全量扫描产出）。
输出 stock/chem_report.html、docs/chem.html、stock/out/chem.svg
"""
import json
import os
import sys
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from stock.universe import UNIVERSE, INDEX   # noqa: E402

# 化工按业务口径取，不按申万分类：恒力、荣盛在申万里归石油石化，但炼化是同一条产业链
CHEM_SYMS = ("sh600309", "sh600426", "sz002648", "sz002601",
             "sh600141", "sh600346", "sz002493", "sh600486")
NAMES = {a.file: a.label for a in UNIVERSE if a.symbol in CHEM_SYMS}
CHEM = list(NAMES.values())
SHORT = {a.label: a.name for a in UNIVERSE}
REF = [INDEX[0].label, "招商银行 600036.SH", "浦发银行 600000.SH", "平安银行 000001.SZ"]
SUB = {"万华化学 600309.SH": "MDI", "华鲁恒升 600426.SH": "煤化工",
       "卫星化学 002648.SZ": "轻烃", "龙佰集团 002601.SZ": "钛白粉",
       "兴发集团 600141.SH": "磷化工", "恒力石化 600346.SH": "炼化",
       "荣盛石化 002493.SZ": "炼化", "扬农化工 600486.SH": "农药"}


def load():
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for name in CHEM + REF:
        last = [x for x in raw[name]["series"] if x["valid"]][-1]
        out[name] = {
            "name": name,
            "short": SHORT.get(name, name),
            "state": last["state"],
            "index": last["index"],
            "regime": last["regime"],
            "tension": last["tension"]["T"],
            "certain": sum(1 for q in last["obs"] if q),
            "suspend": sum(1 for q in last["obs"] if not q),
            "nz": sum(1 for q in last["state"] if q),
            "chem": name in CHEM,
        }
    return out


def tone(r):
    reg = r["regime"]
    if "多头" in reg:
        return "pos"
    if "空头" in reg:
        return "neg"
    if "悬置" in reg:
        return "neu2"
    return "neu"


def make_svg(rows):
    w = 380
    top = 60
    rh = 22
    h = top + len(rows) * rh + 40
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" '
        'aria-label="化工八只与银行参照标的的九维状态矩阵，按 19683 状态索引升序排列">' % (w, h),
        "<style>"
        ".tl{fill:#e8e2d5;font-size:10px}.hd{fill:#87968f;font-size:8.5px}"
        ".nm{fill:#c9d1ca;font-size:9px}.tg{fill:#87968f;font-size:8.5px}"
        ".pos{fill:#5fa79b}.neg{fill:#b5452f}.neu{fill:#6b7a74}.neu2{fill:#c8a45c}"
        "</style>",
        '<rect width="%d" height="%d" fill="#0f1a16"/>' % (w, h),
        '<text x="8" y="16" class="tl">按 19683 态索引升序：左端空头，右端多头</text>',
        '<text x="8" y="32" class="hd">按索引升序，索引是坐标不是距离；化工挤在上半部，末四行是参照</text>',
    ]
    x0 = 62
    cw, gap = 17, 2
    for i, dv in enumerate(["天", "地", "人", "正", "反", "合", "归", "守", "进"]):
        parts.append('<text x="%g" y="49" class="hd" text-anchor="middle">%s</text>'
                     % (x0 + i * (cw + gap) + cw / 2, dv))
    parts.append('<text x="252" y="49" class="hd">索引</text>')
    parts.append('<text x="372" y="49" class="hd" text-anchor="end">张力</text>')
    for r, row in enumerate(rows):
        y = top + r * rh
        if not row["chem"]:
            parts.append('<rect x="0" y="%g" width="380" height="%g" fill="#16231e"/>' % (y, rh - 2))
            parts.append('<rect x="0" y="%g" width="2.5" height="%g" fill="#5fa79b" opacity=".5"/>'
                         % (y, rh - 2))
        parts.append('<text x="8" y="%g" class="nm">%s</text>' % (y + 14, row["short"]))
        for i, v in enumerate(row["state"]):
            cx = x0 + i * (cw + gap)
            fill = 'class="%s" opacity=".9"' % tone(row) if v else 'fill="#1b2723"'
            parts.append('<rect x="%g" y="%g" width="%g" height="13" rx="1.5" %s/>'
                         % (cx, y + 3, cw, fill))
        parts.append('<text x="252" y="%g" class="tg">#%d</text>' % (y + 14, row["index"]))
        parts.append('<text x="372" y="%g" class="tg" text-anchor="end">%.2f</text>'
                     % (y + 14, row["tension"]))
    parts.append('<text x="8" y="%g" class="hd">格子色＝该标的当前市场态：青多头 · 朱空头 · 灰对峙 · 金悬置</text>'
                 % (top + len(rows) * rh + 18))
    parts.append('<text x="8" y="%g" class="hd">暗格＝该维为 0（悬置）　左侧竖条＝参照标的</text>'
                 % (top + len(rows) * rh + 32))
    parts.append("</svg>")
    return "\n".join(parts)


DIST_PICK = ["北京银行 601169.SH", "浦发银行 600000.SH", "招商银行 600036.SH",
             "工商银行 601398.SH", "兴业银行 601166.SH", "华夏银行 600015.SH",
             "中国人寿 601628.SH", "恒力石化 600346.SH"]
SHORT_D = {"北京银行 601169.SH": "北京", "浦发银行 600000.SH": "浦发",
           "招商银行 600036.SH": "招商", "工商银行 601398.SH": "工商",
           "兴业银行 601166.SH": "兴业", "华夏银行 600015.SH": "华夏",
           "中国人寿 601628.SH": "人寿", "恒力石化 600346.SH": "恒力"}


def dist_section():
    from stock import metrics as M
    import json as _json
    with open(os.path.join(HERE, "out", "stock_state.json"), encoding="utf-8") as fh:
        raw = _json.load(fh)
    ref = [x for x in raw["平安银行 000001.SZ"]["series"] if x["valid"]][-1]
    ref_v, ref_i = ref["state"], ref["index"]
    trs = []
    for name in DIST_PICK:
        last = [x for x in raw[name]["series"] if x["valid"]][-1]
        d = M.describe(last["state"], ref_v)
        trs.append(
            "<tr><td>%s</td><td class=\"mono\">%d</td><td class=\"mono\">%d</td>"
            "<td class=\"mono\">%.2f</td><td class=\"mono\">%d / %d</td></tr>"
            % (SHORT_D[name], abs(last["index"] - ref_i), d["hamming"], d["euclid"],
               d["flips"], d["missing"]))
    return DIST_HTML.substitute(rows="\n".join(trs))


DIST_HTML = Template("""<h2>四、索引是坐标，不是距离</h2>
<p>上面的图按索引升序排列。但<b>索引的差值不能当距离</b>——它只是平衡三进制的位置编号。
北京与平安的索引只差 <b>3</b>，浦发与平安差 <b>729</b>，结构上两者都只差一维；
兴业索引差 1461、汉明 3，华夏索引差 3645、汉明 2——<b>索引更远的，结构反而更近</b>。</p>
<p>换成索引差、汉明、欧式、翻转四种口径，答案各不一样：</p>
<table>
<colgroup><col class="d1"><col class="d2"><col class="d3"><col class="d4"><col class="d5"></colgroup>
<thead><tr><th>与平安比</th><th>索引差</th><th>汉明</th><th>欧式</th><th>翻转 / 缺失</th></tr></thead>
<tbody>
$rows
</tbody>
</table>
<p style="color:#87968f;font-size:13px">翻转 = 同一维一边 +1 一边 −1；缺失 = 一边有值一边悬置。
欧式里翻转记 2、缺失记 1。</p>
<div class="note warn">
<span class="k">汉明会在这一步给出相反的排序</span>
华夏汉明 2、工商汉明 3，按汉明华夏更近；欧式给华夏 2.24、工商 1.73，按欧式工商更近。
原因只有一个：华夏是<b>一维反着走</b>，工商是<b>三维没证据</b>。
「方向对立」和「证据不足」被汉明记成同一件事，中段排序就会翻。
顶部不受影响——浦发与北京都是 0 翻转、只缺一维，这才是「离平安最近」这句话站得住的部分。
</div>
<p>另有一条更硬的限制：<b>对全 0 的零态，这三种距离是等价的</b>。零态没有符号，
汉明就等于非零维数，欧式是它的平方根，排序完全一样。
所以「离零 7 层」并不比「有 7 维非零」多说任何信息——原点是那个方向的极值，不是一把更好用的尺子。</p>
""")

def make_html(data):
    chem = sorted([data[n] for n in CHEM], key=lambda r: r["index"])
    refs = [data[n] for n in REF]
    rows_all = sorted(chem + refs, key=lambda r: r["index"])
    bear = [r for r in chem if "空头" in r["regime"]]
    st = [r for r in chem if "对峙" in r["regime"]]
    sus = [r for r in chem if "悬置" in r["regime"]]
    med = sorted(r["tension"] for r in chem)[len(chem) // 2]

    trs = []
    for r in chem:
        trs.append(
            "<tr%s><td>%s</td><td>%s</td><td class=\"mono\">#%d</td><td>%s</td>"
            "<td class=\"mono\">%d/9</td><td class=\"mono\">%.2f</td><td class=\"mono\">%d</td></tr>"
            % (' class="hl"' if "多头" in r["regime"] else "", r["short"], SUB[r["name"]],
               r["index"], r["regime"], r["certain"], r["tension"], r["nz"]))
    bear_names = "、".join(r["short"] for r in bear)
    return TEMPLATE.substitute(
        n=len(chem), nbear=len(bear), med="%.2f" % med, low=min(r["index"] for r in chem),
        svg=make_svg(rows_all), rows="\n".join(trs), bear_names=bear_names,
        dist=dist_section())


TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>化工：九维最冷的一头 · 八只化工标的读数</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%230b1210'/%3E%3Crect x='8' y='8' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='25' y='8' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='42' y='8' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='8' y='25' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='25' y='25' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='42' y='25' width='14' height='14' fill='%236b7a74'/%3E%3Crect x='8' y='42' width='14' height='14' fill='%23b5452f'/%3E%3Crect x='25' y='42' width='14' height='14' fill='%236b7a74'/%3E%3Crect x='42' y='42' width='14' height='14' fill='%23c8a45c'/%3E%3C/svg%3E">
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
.c1{width:19%}.c2{width:13%}.c3{width:15%}.c4{width:19%}.c5{width:10%}.c6{width:12%}.c7{width:12%}
.d1{width:24%}.d2{width:15%}.d3{width:13%}.d4{width:19%}.d5{width:29%}
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
table{font-size:12px}th{font-size:11px}th,td{padding:7px 4px}
.c1{width:18%}.c2{width:14%}.c3{width:14%}.c4{width:21%}.c5{width:9%}.c6{width:12%}.c7{width:12%}
.d1{width:26%}.d2{width:15%}.d3{width:12%}.d4{width:19%}.d5{width:28%}
.mono{font-size:11px}
}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">润泽说 · 认知生命体 v9 · 引擎读数</div>
<h1>化工：九维最冷的一头</h1>
<p class="lead">八只化工标的——MDI、煤化工、轻烃、钛白粉、磷化工、两只炼化、农药——
同一把尺子量下来，它们几乎全部挤在 19683 个状态的最低端。</p>

<div class="bar">
<div><b>$n</b><span>化工样本</span></div>
<div><b class="c">$nbear</b><span>空头确立</span></div>
<div><b class="g">$med</b><span>张力中位</span></div>
<div><b class="c">$low</b><span>最低索引</span></div>
</div>

<figure>
$svg
<figcaption>九维矩阵。格子颜色标的是<b>整只标的的市场态</b>，不是单个维度的取值——暗格才代表该维为 0。横轴按 19683 态索引升序——那是坐标，不是距离，两者差值不可当远近读。</figcaption>
</figure>

<h2>一、全在指数底部，两只完全同态</h2>
<p><b>扬农化工 #174、兴发集团 #183、卫星化学 #183</b>——三个索引挤在 19683 态的 0.9% 分位以内。
兴发与卫星的九维向量<b>一模一样</b>：<span class="mono">[-1,-1,-1,-1,1,-1,1,0,-1]</span>，
两个不同赛道的公司，落进同一个状态。</p>
<p>这个向量与<b>上证指数 #186</b> 只差「守」一格。也就是说：现阶段买磷化工、买轻烃，
在价格行为上和买上证指数没有结构差别。</p>

<h2>二、$nbear 只空头确立，张力 0.70–0.80</h2>
<p>$bear_names——五只判为空头确立。另外，<b>华鲁恒升 #915 与上一轮的中海油 #915 是同一个状态</b>，
煤化工和油气开采落进同一格，这种巧合在这套编码里并不罕见。</p>
<p>对照银行那一头：招商、长电、中国平安也是 8–9 维确定，但方向为多、张力 0.47–0.50。
<b>同样是「八维有值」，一边是 +1 的确定，一边是 −1 的确定。</b>
张力 0.70 以上意味着波动负荷已经很重，跌破 MA20 的深度也够，任何一个反弹都得先扛过这两项。</p>

<div class="note warn">
<span class="k">确定度不等于好</span>
兴发 8/9、扬农 8/9、荣盛 8/9——三个「高确定」，全是空头。
九维告诉你「证据齐不齐」，方向要自己看符号。
</div>

<h2>三、化工内部分层</h2>
<table>
<colgroup><col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6"><col class="c7"></colgroup>
<thead><tr><th>标的</th><th>赛道</th><th>索引</th><th>市场态</th><th>确定</th><th>张力</th><th>实维</th></tr></thead>
<tbody>
$rows
</tbody>
</table>
<p style="color:#87968f;font-size:13px">实维 = 累积态里非 0 的维度数，等价于「离零态的距离」。
19683 态空间的重心在 6 层，越接近 6 越中性，越靠 8–9 越结晶。</p>

$dist
<h2>五、唯一值得再看的一只：万华化学</h2>
<p>万华化学 #3325、张力 0.652、<b>悬置主导</b>，只有 4 维有值——是八只里唯一没有
被空头结构锁死的。它的判断不是「有机会」，而是<b>「证据还不够」</b>：
价格在 67–74 之间来回，均线与量能互相打架，引擎拒绝下结论。</p>
<p>恒力石化 0.400 张力最低，但 2/9 确定、实维 8——低张力来自「什么都没说」，不是「说得很稳」。
这两只的区别是：万华是没定，恒力是没看。</p>

<h2>六、这轮该看什么</h2>
<ul>
<li><b>化工暂时不是「找多头」的地方。</b>八只里零只多头确立，五只空头确立，
方向一致性比银行那头更强——只是一致朝下。</li>
<li><b>看张力回落，不看价格反弹。</b>0.70–0.80 的张力需要一个明确的量能修复才会降，
单日红盘不改读数。</li>
<li><b>如果非要跟踪，盯万华。</b>它是唯一处在「未定」而非「已定」的结构里，
掉维或补维都会先在这一只上出现。</li>
</ul>

<div class="foot">
样本：8 只化工（MDI／煤化工／轻烃／钛白粉／磷化工／炼化／炼化／农药），
2026-10-16 至 11-20 共 26 根日 K，引擎取 21 个有效状态。行情取自新浪财经日线接口，
成交额按「成交量 × 收盘价」估算，量比口径与真实成交额一致。<br>
赛道归类按主营产品，不构成申万行业分类。<br>
本文是结构诊断，不是投资建议。向量相似不等于收益相似，历史状态不保证未来。<br>
引擎 repo：<a href="https://github.com/q1z2q3-debug/cognitive-being-v9">cognitive-being-v9</a>
　·　<a href="./index.html">返回主页</a>　·　<a href="./rank.html">跨行业排名</a>
　·　<a href="./bank-scan.html">同业扫描</a>
</div>
</div>
</body>
</html>
""")


def main():
    data = load()
    rows_all = sorted([data[n] for n in CHEM] + [data[n] for n in REF], key=lambda r: r["index"])
    with open(os.path.join(HERE, "out", "chem.svg"), "w", encoding="utf-8") as f:
        f.write(make_svg(rows_all))
    html = make_html(data)
    for path in (os.path.join(HERE, "chem_report.html"),
                 os.path.join(os.path.dirname(HERE), "docs", "chem.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("wrote", path)


if __name__ == "__main__":
    main()
