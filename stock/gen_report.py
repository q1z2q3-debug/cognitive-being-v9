"""由 stock/out/stock_state.json 生成可视化报告 stock/report.html 与 stock/out/state.svg。"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DATA = json.loads((OUT / "stock_state.json").read_text(encoding="utf-8"))

DIMS = ["天", "地", "人", "正", "反", "合", "归", "守", "进"]
DIM_DESC = {
    "天": "趋势 · 偏离 MA20",
    "地": "量能 · 成交额/20 日均",
    "人": "情绪 · 近 3 日收益",
    "正": "多头证据 · 站上 MA5",
    "反": "空头证据 · 创 10 日新低（+1=反向确认）",
    "合": "一致性 · MA5 与 MA20 同向",
    "归": "位置 · 20 日区间分位",
    "守": "风险 · 振幅相对常态",
    "进": "进攻 · 5 日动量配合量能",
}

COL = {1: "#5fa79b", 0: "#26332e", -1: "#b5452f"}
SYM = {1: "+", 0: "0", -1: "−"}


def norm_series(rows):
    closes = [r["close"] for r in rows]
    base = closes[0]
    return [c / base * 100 for c in closes], closes


def line_path(values, x0=38, x1=336, y_base=118, px_per_pct=8.0, y0=40, y1=152):
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = x0 + (x1 - x0) * i / (n - 1)
        y = y_base + (100 - v) * px_per_pct
        y = max(y0, min(y1, y))
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def build_svg() -> str:
    sh = DATA["上证指数 000001"]
    hs = DATA["沪深300 000300"]
    sh_rows = [s for s in sh["series"] if s["valid"]]
    hs_rows = [s for s in hs["series"] if s["valid"]]
    sh_n, sh_c = norm_series(sh_rows)
    hs_n, hs_c = norm_series(hs_rows)

    p_sh = line_path(sh_n)
    p_hs = line_path(hs_n)

    n = len(sh_rows)
    xs = [38 + (336 - 38) * i / (n - 1) for i in range(n)]
    last_x, last_y = xs[-1], 118 + (100 - sh_n[-1]) * 8.0

    # 九维矩阵
    mat_rows = [
        ("上证·观测", sh["summary"]["last_obs"]),
        ("上证·累积", sh["summary"]["last_state"]),
        ("沪深·观测", hs["summary"]["last_obs"]),
        ("沪深·累积", hs["summary"]["last_state"]),
    ]
    gx, gy, cell, gap = 96, 212, 17, 9
    cells = []
    for r, (label, vec) in enumerate(mat_rows):
        y = gy + r * 26
        cells.append(
            f'<text x="30" y="{y+13}" font-size="10.5" fill="#87968f">{label}</text>'
        )
        for c in range(9):
            x = gx + c * (cell + gap)
            v = vec[c]
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{COL[v]}" '
                f'stroke="#0f1a16" stroke-width="1"/>'
            )
            cells.append(
                f'<text x="{x+cell/2}" y="{y+12}" font-size="9.5" fill="{"#0b1210" if v==1 else "#e8e2d5"}" '
                f'text-anchor="middle" font-family="monospace">{SYM[v]}</text>'
            )
    dim_labels = "".join(
        f'<text x="{gx + c*(cell+gap) + cell/2}" y="205" font-size="10" fill="#b9b3a6" '
        f'text-anchor="middle">{d}</text>'
        for c, d in enumerate(DIMS)
    )

    return f"""<svg viewBox="0 0 360 352" width="100%" role="img" aria-label="上证与沪深300 归一化走势及九维三态状态矩阵" style="display:block">
  <rect x="0" y="0" width="360" height="352" fill="#0b1210"/>
  <text x="30" y="22" font-size="10.5" fill="#5fa79b" font-family="monospace">19 个交易日 · 首日=100</text>
  <line x1="30" y1="118" x2="340" y2="118" stroke="#24352f" stroke-dasharray="3 3"/>
  <text x="338" y="114" font-size="8.5" fill="#5c6f68" text-anchor="end" font-family="monospace">100</text>
  <polyline points="{p_hs}" fill="none" stroke="#c8a45c" stroke-width="1.3" opacity="0.85"/>
  <polyline points="{p_sh}" fill="none" stroke="#5fa79b" stroke-width="1.9"/>
  <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="#b5452f"/>
  <text x="{last_x-6:.1f}" y="{last_y+18:.1f}" font-size="9.5" fill="#e8e2d5" text-anchor="end" font-family="monospace">3533.79</text>
  <text x="30" y="34" font-size="9" fill="#5fa79b" font-family="monospace">上证 -3.14%</text>
  <text x="30" y="47" font-size="9" fill="#c8a45c" font-family="monospace">沪深300 -2.35%</text>
  <line x1="30" y1="186" x2="340" y2="186" stroke="#24352f"/>
  {dim_labels}
  {''.join(cells)}
  <text x="30" y="326" font-size="8.5" fill="#87968f">行=观测/累积 · 列={ ' '.join(DIMS) }</text>
  <text x="30" y="338" font-size="8.5" fill="#87968f">“反”+1 表示空头证据确认，不是利多</text>
</svg>"""


def build_html(svg: str) -> str:
    sh = DATA["上证指数 000001"]["summary"]
    hs = DATA["沪深300 000300"]["summary"]

    why = DATA["上证指数 000001"]["series"][-1]["why"]
    rows = []
    for d, v, s in zip(DIMS, sh["last_obs"], sh["last_state"]):
        cls = "pos" if v == 1 else ("neg" if v == -1 else "zero")
        rows.append(
            f"<tr><td class='dim'>{d}</td><td class='why'>{DIM_DESC[d]}</td>"
            f"<td class='{cls}'>{SYM[v]}</td><td class='{('pos' if s==1 else ('neg' if s==-1 else 'zero'))}'>{SYM[s]}</td>"
            f"<td class='note'>{html.escape(str(why.get(d,'')))}</td></tr>"
        )

    tension_path = json.dumps(
        [{"d": x["date"][4:], "t": x["T"]} for x in sh["tension_path"]], ensure_ascii=False
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>上证 3533.79 · 三值状态诊断</title>
<style>
:root{{--ink:#0b1210;--ink2:#0f1a16;--line:#24352f;--paper:#e8e2d5;--dim:#b9b3a6;--muted:#87968f;--celadon:#5fa79b;--cinnabar:#b5452f;--gold:#c8a45c}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ink);color:var(--paper);font-family:"Noto Serif SC","Songti SC",serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:820px;margin:0 auto;padding:28px 20px 56px}}
.eyebrow{{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.12em;color:var(--muted)}}
h1{{font-size:clamp(26px,4.6vw,38px);line-height:1.25;margin:12px 0 6px;font-weight:700}}
.sub{{color:var(--muted);font-size:13.5px;line-height:1.75;margin-bottom:22px}}
.tagline{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:26px}}
.pill{{font-family:ui-monospace,monospace;font-size:11px;padding:5px 10px;border:1px solid var(--line);color:var(--dim)}}
.pill.hot{{border-color:#5c2f24;color:#d8795c}}
.pill.cool{{border-color:#2c4f4a;color:var(--celadon)}}
h2{{font-size:17px;margin:34px 0 12px;padding-left:10px;border-left:2px solid var(--celadon);font-weight:600}}
h2 span{{font-family:ui-monospace,monospace;font-size:10px;color:var(--muted);letter-spacing:.1em;margin-left:8px;font-weight:400}}
figure{{margin:0;border:1px solid var(--line);background:var(--ink2)}}
figure svg{{display:block}}
figcaption{{font-size:12px;color:var(--muted);padding:10px 14px;border-top:1px solid var(--line);line-height:1.7}}
ul.pts{{margin:0;padding-left:0;list-style:none}}
ul.pts li{{padding:12px 0;border-bottom:1px solid var(--line);font-size:14px;line-height:1.75}}
ul.pts li b{{color:var(--celadon);font-weight:600}}
ul.pts li em{{color:var(--gold);font-style:normal}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}}
th{{text-align:left;font-family:ui-monospace,monospace;font-size:10px;letter-spacing:.1em;color:var(--muted);font-weight:400;padding:0 8px 8px;border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:9px 8px;border-bottom:1px solid var(--line);color:var(--dim)}}
td.dim{{font-family:ui-monospace,monospace;color:var(--paper);font-size:12.5px}}
td.why,td.note{{font-size:11.5px;color:var(--muted)}}
td.pos,td.neg,td.zero{{font-family:ui-monospace,monospace;text-align:center;width:34px}}
td.pos{{color:var(--celadon)}} td.neg{{color:#d8795c}} td.zero{{color:#6b7a74}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);margin-top:8px}}
.cell{{background:var(--ink2);padding:16px}}
.cell .k{{font-family:ui-monospace,monospace;font-size:10px;letter-spacing:.1em;color:var(--muted)}}
.cell .v{{font-size:22px;margin-top:6px;font-weight:600}}
.cell .d{{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.7}}
.note-box{{border:1px solid var(--line);padding:16px;margin-top:20px;font-size:12.5px;color:var(--muted);line-height:1.85}}
.note-box b{{color:var(--dim);font-weight:600}}
footer{{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);font-size:11px;color:var(--muted);font-family:ui-monospace,monospace;line-height:1.9}}
@media(max-width:560px){{
 .grid2{{grid-template-columns:1fr}}
 .cross th:nth-child(4),.cross td:nth-child(4){{display:none}}
 th{{font-size:9.5px;white-space:nowrap}}
 td{{padding:9px 5px}}
 .wrap{{padding:24px 14px 48px}}
 .snap{{display:block;border:0;margin-top:0}}
 .snap thead{{display:none}}
 .snap tbody{{display:block}}
 .snap tr{{display:block;padding:10px 0;border-bottom:1px solid var(--line)}}
 .snap td{{display:inline-block;border:0;padding:0;vertical-align:middle}}
 .snap td.dim{{width:30px;font-size:13px}}
 .snap td.why{{display:none}}
 .snap td.pos,.snap td.neg,.snap td.zero{{width:26px;height:24px;line-height:24px;
   border:1px solid var(--line);margin-left:5px;font-size:12px}}
 .snap td.note{{display:block;width:100%;margin-top:5px;font-size:12px;
   color:var(--muted);white-space:normal;line-height:1.6}}
}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">COGNITIVE BEING v9 · MARKET STATE · 2026.11.20</div>
  <h1>上证 3533.79：空头确立，但位置已到低位</h1>
  <p class="sub">把 19 个交易日的日 K 编码进九维三态基底，得到 19683 态空间里的一个坐标 <b>#186</b>。<br>
  这不是预测，是把“现在处于什么状态”变成一个可复算的对象。</p>

  <div class="tagline">
    <span class="pill cool">状态 空头确立</span>
    <span class="pill hot">张力 {sh['tension']['T']}</span>
    <span class="pill">确定 {sh['determined_dims']}/9</span>
    <span class="pill">悬置 {sh['suspended_dims']}/9</span>
    <span class="pill">19 日 {sh['period_return_pct']:+.2f}%</span>
  </div>

  <figure>
  {svg}
  <figcaption>上：两指数归一化走势（首日=100），朱点为 11/20 收盘，已跌破 10 月低点 3574.27。
  下：11/20 的九维三态矩阵，行分“当日观测”与“累积吸收”，列自上而下为天地人正反合归守进。</figcaption>
  </figure>

  <h2>四条判读 <span>WHAT IT SAYS</span></h2>
  <ul class="pts">
    <li><b>方向已经确立，不是猜测。</b>7 个维度给出确定值，只有量能与风险两维悬置。天（趋势）、正（多头证据）、合（均线一致性）、进（动量）四维同时为 −1。这四维同向在 10/29、11/16 也出现过，但只有今天叠加了反维确认。</li>
    <li><em>但位置在低位。</em>归维 +1：收盘落在近 20 日区间的下沿（约 15% 分位）。低位是反弹的必要条件，不是充分条件——它只说明“下行空间已被压缩”，不说明“会反弹”。</li>
    <li><b>空头证据今天才被确认。</b>反维由 0 跳到 +1，因为收盘 3533.79 跌破了 10 月 23 日的 3574.27。这是 19 日里唯一一次“创阶段新低”被记录，之前的下行都还在区间内。</li>
    <li><em>张力 {sh['tension']['T']}，19 日最高。</em>波动负荷、跌破 MA20 的深度、状态抖动三项同时偏高。在引擎语义里，高张力意味着系统接近需要“转化”的临界点——即旧状态维持成本已经大于重构成本。</li>
  </ul>

  <h2>九维快照 <span>SNAPSHOT</span></h2>
  <table class="snap">
    <thead><tr><th>维</th><th>判据</th><th>观测</th><th>累积</th><th>读数</th></tr></thead>
    <tbody>
    {''.join(rows)}
    </tbody>
  </table>
  <div class="note-box">
    <b>“反”维的方向是反的。</b>+1 表示反向力量被确认（创阶段新低），−1 表示反向力量消失（创阶段新高）。把它当利多是误读。
  </div>

  <h2>机制检验 <span>MECHANISM</span></h2>
  <div class="grid2">
    <div class="cell"><div class="k">观测层直接反转</div><div class="v">{sh['obs_direct_flips']} 维次</div>
      <div class="d">19 日里，同一天从 +1 直接跳到 −1 的次数。市场确实在硬转向。</div></div>
    <div class="cell"><div class="k">累积态直接反转</div><div class="v">{sh['state_direct_flips']} 次</div>
      <div class="d">经过三态吸收后，已确立的判断一次都没有被硬翻，全部先退成 0 悬置再重建。</div></div>
  </div>
  <div class="note-box">
    <b>守恒打破 {sh['conservation_breaks']} 次，不是故障。</b>这是感知吸收在改账本：外部事实进来必然改变三元多重集。
    守卫只守符号层相内演化（实验三 500 步 0 违反），不守感知重分类——这条边界在落库时踩反过，系统会每次掉进全零态。
  </div>

  <h2>对照 <span>CROSS-CHECK</span></h2>
  <table class="cross">
    <thead><tr><th>标的</th><th>今日</th><th>19 日</th><th>累积态</th><th>确定/悬置</th></tr></thead>
    <tbody>
      <tr><td class="dim">上证 000001</td><td class="neg">−1.22%</td><td>{sh['period_return_pct']:+.2f}%</td><td class="dim" style="font-size:11.5px">#186</td><td>7 / 2</td></tr>
      <tr><td class="dim">沪深300 000300</td><td class="neg">−0.76%</td><td>{hs['period_return_pct']:+.2f}%</td><td class="dim" style="font-size:11.5px">#21</td><td>5 / 4</td></tr>
      <tr><td class="dim">深证成指 399001</td><td class="neg">−3.09%</td><td>—</td><td class="dim" style="font-size:11.5px">未编码</td><td>—</td></tr>
    </tbody>
  </table>
  <p class="sub" style="margin-top:12px">上证 159 家上涨 / 2176 家下跌，沪深300 95 / 202。大盘权重抗跌、小盘杀跌的宽度差异，
  在状态上也对得上：沪深300 有 4 维悬置（量能、情绪、位置、风险都没定），上证只有 2 维。</p>

  <h2>边界 <span>LIMITS</span></h2>
  <div class="note-box">
    ① 编码器是<b>固定阈值规则</b>，不是训练模型，没做样本外调参；换窗口或阈值，状态会变。<br>
    ② 样本只有 19 个有效交易日，足以为“当前状态”定位，不足以验证状态的预测力。<br>
    ③ 论文四象相位的汉明最近邻在负向量上会全部误判为“积聚”，本报告<b>没有</b>使用四象相位，
    改用定向度/悬置率的市场态判据——这是工程映射，不是论文原义。<br>
    ④ 本页不含买卖建议，也不构成对未来的预测。
  </div>

  <footer>
    数据：同花顺日 K（2026-10-19 至 2026-11-20，上证/沪深300 各 24 根，前 5 根为均线预热）<br>
    引擎：cognitive-being-v9 · 复现：python -m stock.run<br>
    张力轨迹 0.66 → 0.70（19 日，末值为最高）
  </footer>
</div>
</body>
</html>"""


def main():
    svg = build_svg()
    (OUT / "state.svg").write_text(svg, encoding="utf-8")
    (HERE / "report.html").write_text(build_html(svg), encoding="utf-8")
    print("写出", HERE / "report.html", OUT / "state.svg")


if __name__ == "__main__":
    main()
