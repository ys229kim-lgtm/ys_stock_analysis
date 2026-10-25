#!/usr/bin/env python3
"""
Yahoo Finance chart 엔드포인트로 시세·기술 지표 수집 (API 키 불필요, 표준 라이브러리만 사용).

사용:
  uv run fetch_quote.py --ticker KBH --date 20261025 --output-dir <analyst 폴더>

출력: quote_{date}_{ticker}.json
  price, prev_close, 52주 고저, 50/200일 이동평균, 1M/3M/6M/1Y 수익률, 20일 평균거래량, 최근 20일 종가
yfinance MCP가 rate limit(Too Many Requests)으로 실패할 때의 1차 대체 수단.
"""
import argparse
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "Mozilla/5.0"


def fetch_chart(ticker: str, rng: str = "2y"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)["chart"]["result"][0]


def ret(closes, n):
    if len(closes) <= n or closes[-n - 1] in (None, 0):
        return None
    return round((closes[-1] / closes[-n - 1] - 1) * 100, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()

    res = fetch_chart(a.ticker.upper())
    meta = res["meta"]
    q = res["indicators"]["quote"][0]
    ts = res["timestamp"]
    rows = [(t, c, v) for t, c, v in zip(ts, q["close"], q["volume"]) if c is not None]
    closes = [c for _, c, _ in rows]
    vols = [v for _, _, v in rows if v]
    last_dt = datetime.fromtimestamp(rows[-1][0], tz=timezone.utc).strftime("%Y-%m-%d")

    year = rows[-252:]
    yc = [c for _, c, _ in year]
    out = {
        "ticker": a.ticker.upper(),
        "currency": meta.get("currency"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "last_trading_date": last_dt,
        "price": round(closes[-1], 2),
        "prev_close": round(closes[-2], 2) if len(closes) > 1 else None,
        "day_change_pct": ret(closes, 1),
        "week52_high": round(max(yc), 2),
        "week52_low": round(min(yc), 2),
        "pct_from_52w_high": round((closes[-1] / max(yc) - 1) * 100, 2),
        "ma50": round(statistics.mean(closes[-50:]), 2) if len(closes) >= 50 else None,
        "ma200": round(statistics.mean(closes[-200:]), 2) if len(closes) >= 200 else None,
        "return_1m_pct": ret(closes, 21),
        "return_3m_pct": ret(closes, 63),
        "return_6m_pct": ret(closes, 126),
        "return_1y_pct": ret(closes, 252),
        "avg_volume_20d": round(statistics.mean(vols[-20:])) if len(vols) >= 20 else None,
        "last_20_closes": [round(c, 2) for c in closes[-20:]],
        "source": "Yahoo Finance chart API (비공식, 지연/오류 가능 - 중요 수치는 2차 소스로 교차 확인)",
    }
    outdir = Path(a.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"quote_{a.date}_{a.ticker.upper()}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p}", file=sys.stderr)
    print(json.dumps({"output": str(p), "price": out["price"], "as_of": last_dt}, ensure_ascii=False))


if __name__ == "__main__":
    main()
