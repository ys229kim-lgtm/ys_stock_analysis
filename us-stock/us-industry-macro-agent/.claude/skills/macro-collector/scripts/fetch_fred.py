#!/usr/bin/env python3
"""
FRED 공개 CSV 엔드포인트로 거시 지표 수집 (API 키 불필요, 표준 라이브러리만 사용).

사용:
  uv run fetch_fred.py --date 20261025 --output-dir <industry 폴더> [--series DGS10,DGS2,...]

출력: macro_{date}.json - 시리즈별 최신값, 1주/1개월/3개월/1년 전 값, 변화량
기본 시리즈: 금리·모기지·물가·고용·신용스프레드 (주택/소비/금융 업종에 유용)
"""
import argparse
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_SERIES = {
    "DFF": "연방기금금리 (실효, 일간)",
    "DGS2": "미 국채 2년 (%)",
    "DGS10": "미 국채 10년 (%)",
    "T10Y2Y": "10Y-2Y 스프레드 (%p)",
    "MORTGAGE30US": "30년 고정 모기지 (Freddie Mac, 주간 %)",
    "CPIAUCSL": "CPI (지수, 월간) - YoY는 별도 계산",
    "UNRATE": "실업률 (%)",
    "BAMLH0A0HYM2": "하이일드 스프레드 (ICE BofA, %p)",
    "HOUST": "주택착공 (천 채, 연율)",
    "HSN1F": "신규주택 판매 (천 채, 연율)",
    "UMCSENT": "미시간대 소비자심리지수",
}
UA = "Mozilla/5.0 stock-analysis-agent"


def fetch(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        text = r.read().decode("utf-8")
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        keys = list(rec.keys())
        v = rec[keys[1]]
        if v not in ("", ".", None):
            rows.append((rec[keys[0]], float(v)))
    return rows


def value_at(rows, target: datetime):
    """target 이전(포함) 마지막 관측치."""
    best = None
    for dt, v in rows:
        if datetime.strptime(dt, "%Y-%m-%d") <= target:
            best = (dt, v)
        else:
            break
    return best


def summarize(sid: str, rows):
    last_dt, last_v = rows[-1]
    last = datetime.strptime(last_dt, "%Y-%m-%d")
    out = {"latest": {"date": last_dt, "value": last_v}}
    for label, days in (("1w", 7), ("1m", 30), ("3m", 91), ("1y", 365)):
        p = value_at(rows, last - timedelta(days=days))
        if p:
            out[f"ago_{label}"] = {"date": p[0], "value": p[1], "change": round(last_v - p[1], 3)}
    if sid == "CPIAUCSL":
        p = value_at(rows, last - timedelta(days=365))
        if p:
            out["yoy_pct"] = round((last_v / p[1] - 1) * 100, 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--series", default=",".join(DEFAULT_SERIES))
    a = ap.parse_args()

    result, errors = {}, {}
    for sid in [s.strip() for s in a.series.split(",") if s.strip()]:
        try:
            rows = fetch(sid)
            result[sid] = {"description": DEFAULT_SERIES.get(sid, ""), **summarize(sid, rows)}
        except Exception as e:  # 네트워크/시리즈 오류는 건너뛰고 기록
            errors[sid] = str(e)
    out = {"source": "FRED (fred.stlouisfed.org CSV)", "collected_for": a.date, "series": result, "errors": errors}
    outdir = Path(a.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"macro_{a.date}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p} ({len(result)} series, {len(errors)} errors)", file=sys.stderr)
    print(json.dumps({"output": str(p), "ok": list(result), "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
