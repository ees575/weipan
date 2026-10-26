"""实时行情：腾讯 qt.gtimg.cn 快照（约 3 秒刷新）+ 新浪 5 分钟历史。

分秒级说明：
  - 免费源的真实刷新频率是 3 秒，轮询 0.4s 只是让"发现变化"的延迟最小；
  - 要真正逐笔，需要 Level-2（券商 API）或 QMT 行情，这里留了 QMT 接口。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

_TX = "http://qt.gtimg.cn/q="
_SINA_MIN = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
             "CN_MarketData.getKLineData?symbol={sym}&scale=5&ma=no&datalen={n}")

_session = requests.Session()
_session.trust_env = False          # 忽略系统代理，否则被本机代理掐断
_session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/130"
_session.headers["Referer"] = "https://finance.sina.com.cn"


def norm(code: str) -> str:
    """600519 / USHA600519 / sh600519 / 600519.SH → sh600519"""
    c = code.strip().upper().replace("USHA", "sh").replace("USZA", "sz").replace("USTM", "bj")
    if c.startswith(("SH", "SZ", "BJ")) and len(c) >= 8:
        return c.lower()
    c = c.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    if c.startswith(("6", "9", "5")):
        return "sh" + c
    if c.startswith(("0", "3", "1", "2")):
        return "sz" + c
    return "bj" + c


@dataclass
class Quote:
    code: str
    name: str
    price: float
    prev_close: float
    open: float
    high: float
    low: float
    volume: float          # 手
    amount: float          # 元
    bids: list[tuple[float, int]] = field(default_factory=list)
    asks: list[tuple[float, int]] = field(default_factory=list)
    ts: float = field(default_factory=time.time)
    raw_time: str = ""

    @property
    def pct(self) -> float:
        return (self.price / self.prev_close - 1) * 100 if self.prev_close else 0.0

    @property
    def turnover(self) -> float:            # 换手率 %
        return float(self._turnover)

    _turnover: float = 0.0


def _f(parts: list[str], i: int, default: float = 0.0) -> float:
    try:
        return float(parts[i])
    except (IndexError, ValueError):
        return default


def quotes(codes: list[str]) -> dict[str, Quote]:
    """批量快照，一次最多 ~60 只。"""
    if not codes:
        return {}
    syms = [norm(c) for c in codes]
    out: dict[str, Quote] = {}
    for i in range(0, len(syms), 60):
        chunk = syms[i:i + 60]
        r = _session.get(_TX + ",".join(chunk), timeout=6)
        text = r.content.decode("gb18030", "ignore")
        for line in text.split(";"):
            line = line.strip()
            if "=" not in line or '"' not in line:
                continue
            body = line.split('"')[1]
            p = body.split("~")
            if len(p) < 40:
                continue
            q = Quote(
                code=norm(p[2]), name=p[1],
                price=_f(p, 3), prev_close=_f(p, 4), open=_f(p, 5),
                volume=_f(p, 6), amount=_f(p, 37) * 1e4,
                high=_f(p, 33), low=_f(p, 34), raw_time=p[30] if len(p) > 30 else "",
            )
            q._turnover = _f(p, 38)
            q.bids = [(_f(p, 9 + 2 * k), int(_f(p, 10 + 2 * k))) for k in range(5)]
            q.asks = [(_f(p, 19 + 2 * k), int(_f(p, 20 + 2 * k))) for k in range(5)]
            out[q.code] = q
    return out


def history_5min(code: str, n: int = 320) -> list[dict]:
    """新浪 5 分钟 K 线，最多约 1023 根（≈21 个交易日），回测用。"""
    sym = norm(code)
    r = _session.get(_SINA_MIN.format(sym=sym, n=n), timeout=15)
    data = r.json() or []
    return [{"dt": x["day"], "open": float(x["open"]), "high": float(x["high"]),
             "low": float(x["low"]), "close": float(x["close"]), "volume": float(x["volume"])}
            for x in data]


def now_hhmmss() -> str:
    return time.strftime("%H:%M:%S")
