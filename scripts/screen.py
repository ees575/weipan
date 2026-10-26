"""GitHub Actions 版：每次运行扫描全市场，生成静态页面到 docs/。

不依赖任何人的电脑——GitHub 的服务器跑。
刷新频率 = cron 频率（5 分钟一次，交易时段）。
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import feed  # noqa: E402

TRADEABLE = ("600", "601", "603", "605", "000", "001", "002", "003")
BASE_EARLY = 1.30
RET_D = {(-11, -5): -0.33, (-5, -2): -0.17, (-2, 0): -0.10, (0, 2): 0.03,
         (2, 4): 0.11, (4, 6): 0.26, (6, 8): 0.73, (8, 9.8): 0.45, (9.8, 11): 0.60}
D60_D = {(-100, -30): 0.04, (-30, -15): 0.08, (-15, -8): 0.09, (-8, -4): -0.17,
         (-4, -2): -0.42, (-2, 0): -0.94, (0, 100): 0.30}
POS_D = {(0, 0.2): -0.28, (0.2, 0.4): 0.05, (0.4, 0.6): 0.21, (0.6, 0.8): 0.10, (0.8, 1.01): 0.12}
IMDD_D = {(-100, -6): 0.39, (-6, -4): 0.25, (-4, -2): 0.04, (-2, -1): -0.15, (-1, 1): -0.24}
ATR_D = {(0, 3): -0.25, (3, 5): 0.05, (5, 7): 0.20, (7, 9): 0.30, (9, 100): 0.35}


def binof(v, table):
    for k in table:
        if k[0] <= v < k[1]:
            return table[k]
    return 0.0


def universe() -> dict:
    s = requests.Session()
    s.trust_env = False
    try:
        s.post("http://124.221.98.135:5002/login",
               json={"username": "ees", "password": "dahan521.."}, timeout=20)
        uni = s.get("http://124.221.98.135:5002/api/quant/pool?type=", timeout=60).json()["data"]
    except Exception:
        return {}
    out = {}
    for x in uni:
        c = x.get("full_code") or x["code"]
        if not str(c)[-6:].startswith(TRADEABLE):
            continue
        nm = str(x.get("name") or "")
        if "ST" in nm or "退" in nm:
            continue
        out[c] = nm
    return out


def quotes_all(codes):
    out = {}
    batches = [codes[i:i + 50] for i in range(0, len(codes), 50)]

    def g(ch):
        try:
            return feed.quotes(ch)
        except Exception:
            return {}

    with ThreadPoolExecutor(max_workers=16) as ex:
        for fu in as_completed([ex.submit(g, b) for b in batches]):
            out.update(fu.result())
    return out


def main():
    names = universe()
    if not names:
        print("股票池获取失败")
        return
    print(f"标的 {len(names)}")
    qs = quotes_all(list(names))
    rows = []
    for code, q in qs.items():
        if not q or q.price <= 0 or q.amount < 5e7 or not (2 <= q.price <= 200):
            continue
        p = q.pct
        pos = (q.price - q.low) / (q.high - q.low) if q.high > q.low else 0.5
        e = BASE_EARLY + (binof(p, RET_D) + binof(pos, POS_D)) * 0.55
        rows.append({"code": code, "name": names.get(code, q.name), "price": round(q.price, 2),
                     "pct": round(p, 2), "amount": round(q.amount / 1e8, 2),
                     "pos": round(pos, 2), "expected": round(max(-1.5, min(6.0, e)), 2),
                     "buyable": p < 9.8})
    rows.sort(key=lambda x: (not x["buyable"], -x["expected"]))
    top = rows[:40]
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>尾盘摸高选股</title><style>
body{{margin:0;background:#080b10;color:#e8eef5;font:14px/1.6 "Microsoft YaHei",sans-serif}}
header{{padding:14px 18px;border-bottom:1px solid #1c2632}}
h1{{font-size:17px;margin:0 0 6px}}
.m{{color:#8494a6;font-size:12px}}
table{{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}}
th,td{{padding:7px 6px;border-bottom:1px solid #141c26;text-align:right;white-space:nowrap}}
th{{color:#8494a6;font-size:11px;font-weight:500}}
th:nth-child(1),th:nth-child(2),th:nth-child(3),td:nth-child(1),td:nth-child(2),td:nth-child(3){{text-align:left}}
.up{{color:#ff4d4f}}.dn{{color:#22c55e}}.e{{color:#ffcc55;font-weight:700}}
.g{{opacity:.45}}main{{padding:10px 18px 40px}}
</style></head><body>
<header><h1>尾盘摸高选股</h1>
<div class="m">更新时间 {ts} ｜ 标的 {len(names)} 只 ｜ 榜单 {len(top)} 只 ｜ 由 GitHub Actions 自动刷新（约 5 分钟一次）</div></header>
<main><table><thead><tr><th>预测摸高</th><th>名称</th><th>代码</th><th>现价</th><th>涨幅</th><th>收盘位置</th><th>成交额</th></tr></thead><tbody>
""" + "".join(
        f'<tr class="{"g" if not r["buyable"] else ""}"><td class="e">{r["expected"]:.2f}%</td>'
        f'<td>{r["name"]}</td><td>{r["code"]}</td><td>{r["price"]}</td>'
        f'<td class="{"up" if r["pct"]>=0 else "dn"}">{r["pct"]:+.2f}%</td>'
        f'<td>{r["pos"]:.2f}</td><td>{r["amount"]:.2f}亿</td></tr>' for r in top
    ) + "</tbody></table></main></body></html>"

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(html, encoding="utf-8")
    (docs / "data.json").write_text(json.dumps({"ts": ts, "rows": top}, ensure_ascii=False),
                                    encoding="utf-8")
    print(f"已生成 docs/index.html，榜单 {len(top)} 只，时间 {ts}")


if __name__ == "__main__":
    main()
