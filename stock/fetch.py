"""从新浪日 K 接口抓标的池行情，落 `stock/data/<symbol>.csv`。

标的清单来自 `stock/universe.py`，这里不写死任何代码。
窗口固定为最近 KEEP 根日 K —— 全部标的同一根窗口，否则日期错位会让距离不可比。

用法（仓库根目录）：
    python -m stock.fetch            # 全部
    python -m stock.fetch sh600585   # 单只
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

from stock.universe import UNIVERSE, Asset

DATA = Path(__file__).resolve().parent / "data"
URL = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=32"
)
KEEP = 26          # 与既有报告一致：26 根
RETRY = 2


def grab(a: Asset) -> Tuple[Asset, int]:
    last: Exception | None = None
    for _ in range(RETRY + 1):
        try:
            raw = urllib.request.urlopen(URL.format(symbol=a.symbol), timeout=20).read().decode()
            bars = json.loads(raw)
            if len(bars) < KEEP:
                raise ValueError(f"只有 {len(bars)} 根，不足 {KEEP}")
            bars = bars[-KEEP:]
            rows: List[List[str]] = []
            for b in bars:
                close = float(b["close"])
                amount = float(b["volume"]) * close / 1e8   # 成交额估算：量 × 收盘
                rows.append([
                    b["day"].replace("-", ""), b["open"], b["high"], b["low"], b["close"],
                    f"{amount:.2f}",
                ])
            with open(DATA / a.file, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["date", "open", "high", "low", "close", "amount_yi"])
                w.writerows(rows)
            return a, len(rows)
        except Exception as e:                      # 网络抖动 / 停牌缺根
            last = e
            time.sleep(1.5)
    raise RuntimeError(f"{a.symbol} {a.name}: {last}")


def main() -> Dict[str, int]:
    wanted = sys.argv[1:]
    targets = [a for a in UNIVERSE if not wanted or a.symbol in wanted or a.code in wanted]
    ok: List[str] = []
    bad: List[str] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(grab, a): a for a in targets}
        for fut in as_completed(futs):
            a = futs[fut]
            try:
                fut.result()
                ok.append(a.symbol)
            except Exception as e:
                bad.append(str(e))
    print(f"抓到 {len(ok)} / {len(targets)}")
    for b in bad:
        print("  失败:", b)
    # 窗口一致性自检：所有文件首尾日期必须相同
    heads, tails = set(), set()
    for a in targets:
        p = DATA / a.file
        if not p.exists():
            continue
        with open(p, newline="", encoding="utf-8") as f:
            r = list(csv.DictReader(f))
        if r:
            heads.add(r[0]["date"])
            tails.add(r[-1]["date"])
    print("首日:", sorted(heads), " 末日:", sorted(tails))
    if len(heads) != 1 or len(tails) != 1:
        print("!! 窗口不一致，距离不可比")
    return {"ok": len(ok), "total": len(targets), "bad": len(bad)}


if __name__ == "__main__":
    main()
