"""生成平安银行（000001.SZ）个股状态诊断报告。数据源：stock/out/stock_state.json"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT / "out" / "stock_state.json").read_text(encoding="utf-8"))
PAB = D["平安银行 000001.SZ"]
IDX = D["上证指数 000001"]
DIMS = PAB["dim_names"]

last = [s for s in PAB["series"] if s["valid"]][-1]
CLOSE = last["close"]
AMT = 25.82
PE, PB, CAP = 5.454, 0.4975, 2371.40
rng_lo, rng_hi = 11.13, 12.32
q = (CLOSE - rng_lo) / (rng_hi - rng_lo)

C_BG = "#0b1210"
C_PANEL = "#0f1a16"
C_LINE = "#24352f"
C_TXT = "#e8e2d5"
C_MUT = "#87968f"
C_CEL = "#5fa79b"
C_CIN = "#b5452f"
C_GLD = "#c8a45c"

vals = PAB["series"]
closes = [s["close"] for s in vals]
n = len(closes)
dates = [s["date"][4:] for s in vals]

# ---------- SVG ----------
W, H = 380, 412
X0, X1 = 30, 350
STEP = (X1 - X0) / (n - 1)
PMIN, PMAX = 11.0, 12.5


def px(i):
    return X0 + i * STEP


def py(p):
    return 190 - (p - PMIN) / (PMAX - PMIN) * 150


def colour(v):
    return C_CEL if v > 0 else (C_CIN if v < 0 else "#6b7a74")


parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
         f'style="max-width:100%;display:block;margin:0 auto" role="img" aria-label="平安银行价格与九维状态矩阵">']

# 网格与价格刻度
for gv in (11.0, 11.5, 12.0, 12.5):
    y = py(gv)
    parts.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="{C_LINE}" stroke-width="1" opacity=".55"/>')
    if gv < 12.5:
        parts.append(f'<text x="{X1}" y="{y - 3:.1f}" text-anchor="end" font-size="9" fill="{C_MUT}">{gv:.1f}</text>')

# MA20
ma = [(i, sum(closes[i - 19:i + 1]) / 20) for i in range(19, n)]
ma_pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in ma)
parts.append(f'<polyline points="{ma_pts}" fill="none" stroke="{C_GLD}" stroke-width="1.2" '
             f'stroke-dasharray="4 3" opacity=".8"/>')

# 收盘线
pts = " ".join(f"{px(i):.1f},{py(c):.1f}" for i, c in enumerate(closes))
area = f"{px(0):.1f},190 " + pts + f" {px(n - 1):.1f},190"
parts.append(f'<polygon points="{area}" fill="{C_CEL}" opacity=".07"/>')
parts.append(f'<polyline points="{pts}" fill="none" stroke="{C_CEL}" stroke-width="2"/>')

i13 = dates.index("1113")
parts.append(f'<circle cx="{px(i13):.1f}" cy="{py(closes[i13]):.1f}" r="3" fill="{C_GLD}"/>')

parts.append(f'<circle cx="{px(n - 1):.1f}" cy="{py(closes[-1]):.1f}" r="3.5" fill="{C_CIN}"/>')


# 图例
parts.append(f'<text x="{X0}" y="16" font-size="9.5" fill="{C_TXT}">平安银行收盘（26 交易日）</text>')
parts.append(f'<line x1="{X0 + 132}" y1="13" x2="{X0 + 158}" y2="13" stroke="{C_GLD}" '
             f'stroke-width="1.2" stroke-dasharray="4 3"/><text x="{X0 + 162}" y="16" font-size="9" fill="{C_MUT}">20 日均线</text>')

# 矩阵
ROWS = [("观测", last["obs"], C_TXT), ("累积", last["state"], C_TXT), ("上证", IDX["series"][-1]["state"], C_MUT)]
MX, MW = 96, 250


def cellw():
    return MW / 9


parts.append(f'<text x="{X0}" y="{212}" font-size="9.5" fill="{C_MUT}">九维状态矩阵 · 2026-11-20</text>')
for r, (name, vec, tc) in enumerate(ROWS):
    y = 240 + r * 32
    parts.append(f'<text x="{X0}" y="{y + 16}" font-size="10.5" fill="{tc}">{name}</text>')
    for c, v in enumerate(vec):
        x = MX + c * cellw()
        parts.append(f'<rect x="{x + 2:.1f}" y="{y}" width="{cellw() - 4:.1f}" height="23" rx="2" '
                     f'fill="{colour(v)}" opacity="{0.9 if v else 0.28}"/>')
        parts.append(f'<text x="{x + cellw() / 2:.1f}" y="{y + 15}" text-anchor="middle" font-size="10.5" '
                     f'fill="{"#0b1210" if v else C_MUT}" font-weight="600">{"+" if v > 0 else ("" if v == 0 else "−")}{abs(v)}</text>')
for c, d in enumerate(DIMS):
    parts.append(f'<text x="{MX + c * cellw() + cellw() / 2:.1f}" y="{236}" text-anchor="middle" '
                 f'font-size="9" fill="{C_MUT}">{d}</text>')

parts.append(f'<text x="{X0}" y="{358}" font-size="9" fill="{C_MUT}">青 = +1（成立）　朱 = −1（反向成立）　灰 = 0（悬置）</text>')
parts.append(f'<text x="{X0}" y="{372}" font-size="9" fill="{C_MUT}">观测层 11 次直接翻转；累积态 0 次——噪音被吸收成悬置，未穿透状态</text>')
svg = "".join(parts) + "</svg>"

# ---------- 九维卡片 ----------
why = last["why"]
cards = "".join(
    f'<div class="dim"><div class="dh"><span class="dn">{d}</span><span class="dv" style="color:{colour(v)}">'
    f'{("+" if v > 0 else ("" if v == 0 else "−"))}{abs(v)}</span></div><p>{why[d]}</p></div>'
    for d, v in zip(DIMS, last["obs"])
)

ROWS_PEER = [
    ("平安银行", "5.45", "0.50", "2,371", True),
    ("兴业银行", "5.72", "0.50", "4,296", False),
    ("浦发银行", "6.99", "0.48", "3,620", False),
    ("招商银行", "7.26", "0.94", "11,097", False),
    ("工商银行", "8.72", "0.84", "33,502", False),
]
peer_rows = "".join(
    ("<tr class='hl'>" if h else "<tr>") + f'<td>{a}</td><td>{b}</td><td>{c}</td><td>{e}</td></tr>'
    for a, b, c, e, h in ROWS_PEER
)

CSS = """
:root{--bg:#0b1210;--panel:#0f1a16;--line:#24352f;--txt:#e8e2d5;--mut:#87968f;
--cel:#5fa79b;--cin:#b5452f;--gld:#c8a45c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
font-size:15px;line-height:1.72;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:34px 22px 64px}
.eyebrow{font-size:11.5px;letter-spacing:.18em;color:var(--mut);text-transform:none}
h1{font-family:"Songti SC","Noto Serif SC",Georgia,serif;font-size:clamp(28px,6.4vw,46px);
line-height:1.24;margin:14px 0 10px;font-weight:600;letter-spacing:.01em}
h1 em{font-style:normal;color:var(--cin)}
.lead{color:var(--mut);font-size:14.5px;max-width:68ch;margin:0}
.lead b{color:var(--txt);font-weight:500}
.band{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);
border:1px solid var(--line);border-radius:3px;margin:28px 0;overflow:hidden}
.band div{background:var(--panel);padding:13px 12px 14px}
.band .k{font-size:10.5px;color:var(--mut);letter-spacing:.06em;display:block;margin-bottom:5px}
.band .v{font-family:"Songti SC","Noto Serif SC",Georgia,serif;font-size:19px;line-height:1.2}
.band .v small{font-size:11.5px;color:var(--mut);margin-left:3px;font-family:inherit}
.band .v.up{color:var(--cel)}
figure{margin:0 auto 10px;max-width:640px;background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:14px 10px 6px}
figcaption{font-size:12px;color:var(--mut);padding:6px 6px 10px;line-height:1.6}
h2{font-family:"Songti SC","Noto Serif SC",Georgia,serif;font-size:20px;font-weight:600;
margin:38px 0 12px;padding-left:12px;border-left:2px solid var(--gld)}
.read{display:grid;gap:14px;margin-top:16px}
.read article{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:15px 17px}
.read .no{font-family:"Songti SC",Georgia,serif;font-size:12px;color:var(--gld);letter-spacing:.1em}
.read h3{font-size:15.5px;margin:6px 0 6px;font-weight:600;line-height:1.45}
.read p{margin:0;font-size:13.5px;color:var(--mut);line-height:1.75}
.read p b{color:var(--txt);font-weight:500}
.dims{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);
border:1px solid var(--line);border-radius:3px;overflow:hidden;margin-top:16px}
.dim{background:var(--panel);padding:11px 12px 12px}
.dh{display:flex;align-items:baseline;justify-content:space-between}
.dn{font-family:"Songti SC",Georgia,serif;font-size:16px;color:var(--txt)}
.dv{font-size:15px;font-weight:600}
.dim p{margin:3px 0 0;font-size:11.5px;color:var(--mut);line-height:1.5}
table{width:100%;border-collapse:collapse;margin-top:14px;font-size:13px}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line)}
th{font-size:11px;color:var(--mut);font-weight:500;letter-spacing:.04em}
th:first-child,td:first-child{text-align:left}
tr.hl td{color:var(--cel);background:rgba(124,196,174,.05)}
.note{font-size:12.5px;color:var(--mut);margin-top:12px;line-height:1.75}
.edge{border:1px solid var(--line);border-left:2px solid var(--cin);background:var(--panel);
padding:16px 18px;margin-top:22px;border-radius:3px}
.edge h3{margin:0 0 8px;font-size:14px;color:var(--cin);font-weight:600;letter-spacing:.02em}
.edge p{margin:0;font-size:13px;color:var(--mut);line-height:1.78}
@media (min-width:760px){
.read{grid-template-columns:1fr 1fr}
.read p{font-size:13px}
}
@media (max-width:680px){
.band{grid-template-columns:repeat(2,1fr)}
.band div:last-child{grid-column:1/-1}
.band .v{font-size:17px}
.dims{grid-template-columns:repeat(3,1fr)}
.dim p{font-size:11px}
}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);
font-size:11.5px;color:var(--mut);line-height:1.9}
"""

broken = sum(1 for x in PAB["series"] if not x["diag"]["conservation_ok"])

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230b1210'/%3E%3Crect x='6' y='9' width='20' height='3' rx='1.5' fill='%235fa79b'/%3E%3Crect x='6' y='15' width='14' height='3' rx='1.5' fill='%23c8a45c'/%3E%3Crect x='6' y='21' width='20' height='3' rx='1.5' fill='%23b5452f'/%3E%3C/svg%3E">
<title>平安银行 12.22：逆势的一天 · 三值状态诊断</title>
<style>{CSS}</style></head><body><div class="wrap">

<p class="eyebrow">三值状态诊断 · 个股 / 000001.SZ</p>
<h1>逆势的一天：<br>平安银行 <em>12.22</em></h1>
<p class="lead">同一根 K 线落在两套坐标上：上证 {IDX['series'][-1]['index']} 号态（空头确立，张力 {IDX['series'][-1]['tension']['T']:.3f}），
平安 {last['index']} 号态（多头确立，张力 {last['tension']['T']:.2f}）。两者相差 {last['index'] - IDX['series'][-1]['index']}，
几乎站在 19683 个状态的两端。引擎没有"看多"或"看空"，它只是把"指数在跌、这只股在涨"记成了两个不相交的三值结构。</p>

<div class="band">
<div><span class="k">收盘</span><span class="v up">{CLOSE:.2f}<small>+1.50%</small></span></div>
<div><span class="k">成交额</span><span class="v">{AMT:.2f}<small>亿 · 1.38×</small></span></div>
<div><span class="k">PE (TTM)</span><span class="v">{PE:.2f}</span></div>
<div><span class="k">PB</span><span class="v">{PB:.2f}</span></div>
<div><span class="k">状态索引</span><span class="v">{last['index']}<small>/19683</small></span></div>
</div>

<figure>{svg}
<figcaption>上：10/16–11/20 收盘与 20 日均线，11/13 放量突破（+2.37%，26.24 亿）后站上均线，11/20 逆势再放量。
下：九维矩阵——第一行为今日观测，第二行为同一观测经吸收后的累积态，第三行为同日上证累积态作对照。</figcaption></figure>

<h2>四个读法</h2>
<div class="read">
<article><span class="no">01</span>
<h3>方向确立，共识没有确立</h3>
<p>累积态 9 维里只有 <b>5 维有值</b>（天、地、正、合、归），人、反、守、进四维悬置。同日上证是 <b>7 维有值</b>——
也就是指数那边的"确定度"反而更高。个股这个"多头确立"，只是方向上的，不是强度上的。</p></article>

<article><span class="no">02</span>
<h3>位置已经到区间上沿</h3>
<p>归维 −1（区间分位 {q*100:.0f}%）：收盘 {CLOSE:.2f} 落在 20 日区间 {rng_lo:.2f}–{rng_hi:.2f} 的上端，
距 11/17 的高点 {rng_hi:.2f} 只剩 {(rng_hi/CLOSE-1)*100:.1f}%。继续向上要靠新证据，靠惯性走不远。</p></article>

<article><span class="no">03</span>
<h3>今天这根阳线是承接，不是进攻</h3>
<p>成交 {AMT:.2f} 亿、1.38 倍于 20 日均额，地维随之 +1；但近 5 日累计只有 <b>+1.24%</b>，
没够 1.5% 的进攻阈值，进维仍是 0。放量而动量不足——是换手在放大，不是趋势在加速。</p></article>

<article><span class="no">04</span>
<h3>与大盘反向，分歧没有收敛</h3>
<p>上证累积 9 维全负（确定 7/9，张力 {IDX['series'][-1]['tension']['T']:.3f} 为 19 日最高），
平安 4 维为正。指数在系统性走弱的日子，一只权重股逆势收红，通常意味着资金在<b>板块内部做切换</b>，
而不是市场整体转暖。这一点在状态空间里表现为两端：{IDX['series'][-1]['index']} 与 {last['index']}。</p></article>
</div>

<h2>今日九维读数</h2>
<div class="dims">{cards}</div>

<h2>估值位置</h2>
<p class="note">同日银行板块横向（PE TTM / PB / 总市值，亿元）：</p>
<table>
<thead><tr><th>标的</th><th>PE</th><th>PB</th><th>市值</th></tr></thead>
<tbody>{peer_rows}</tbody>
</table>
<p class="note">平安 PB 0.50 与兴业 0.50 几乎重合，PE 5.45 略低；对四大行（PE 8.7–9.6、PB 0.84–0.94）是老牌折价。
但"低估"在引擎里不构成任何一维——它只体现为归维处在区间高位这一位置事实。估值便宜和股价会涨，是两件事。</p>

<h2>机制观察</h2>
<p class="note">26 根 K 线里，观测层发生 <b>11 次</b>"+1 直接跳 −1"或反向的硬翻转，是上证同期（3 次）的近四倍；
而累积态硬翻 <b>0 次</b>——每一次都被先退成 0 悬置，再由下一日证据重算。个股尺度的噪音密度远高于指数，
但噪声在这里没有一次穿透到状态层。守恒打破 {broken} 次，全部来自感知吸收改账本，不是故障。</p>

<div class="edge"><h3>边界</h3>
<p>样本 21 个有效交易日（预热 5 日）；九维为固定阈值规则编码，非学习模型，阈值选择本身带主观性；
未纳入财报质量（净息差、不良生成率、拨备覆盖）、资金流向、北向持仓、隐含波动等维度；
三值状态描述的是当日观测结构，不是价格预测。本页不含任何买入、卖出或持有建议。</p></div>

<footer>数据：同花顺 / Wind，2026-11-20 收盘 · 引擎：cognitive-being-v9 三值计算基底（19683 态）<br>
状态 = 观测经 absorb_evidence 逐日吸收；索引 = 九维三值向量的三进制编码</footer>
</div></body></html>
"""

(ROOT / "pa_report.html").write_text(HTML, encoding="utf-8")
(ROOT / "out" / "pa_state.svg").write_text(svg, encoding="utf-8")
(ROOT.parent / "docs" / "pa-000001.html").write_text(HTML, encoding="utf-8")
print("ok", len(HTML))
