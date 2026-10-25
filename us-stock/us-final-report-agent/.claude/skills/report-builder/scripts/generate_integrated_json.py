#!/usr/bin/env python3
"""
통합 JSON 생성: normalized_summary.json + scenarios.json -> integrated_{date}_{TICKER}.json
(generate_docx.py 표지가 summary 블록을 읽으므로 가격 필드는 통화기호 포함 문자열로 만든다.)

사용:
  uv run generate_integrated_json.py --ticker KBH --company "KB Home" --date 20261025 --final-path <final 폴더>
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def money(v, cur="USD"):
    sym = {"USD": "$"}.get(cur, "")
    return f"{sym}{v:,.2f}" if isinstance(v, (int, float)) else "N/A"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--final-path", required=True)
    a = ap.parse_args()

    fd = Path(a.final_path)
    norm_p, sc_p = fd / "normalized_summary.json", fd / "scenarios.json"
    if not norm_p.exists():
        sys.exit(f"[ERROR] normalized_summary.json 없음: {norm_p}")
    norm = json.loads(norm_p.read_text(encoding="utf-8"))
    scen = json.loads(sc_p.read_text(encoding="utf-8")) if sc_p.exists() else {}
    cur = norm.get("currency", "USD")
    vs = norm["valuation_summary"]
    wa, fvr = vs["weighted_avg"], vs["fair_value_range"]

    integrated = {
        "meta": {"company": a.company, "ticker": a.ticker.upper(), "analysis_date": a.date, "currency": cur,
                 "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 "agent_version": "us-final-report-agent v1.0"},
        "summary": {
            "company": a.company, "ticker": a.ticker.upper(), "analysis_date": a.date,
            "current_price": money(norm.get("current_price"), cur),
            "weighted_avg_fair_value": money(wa.get("mid"), cur),
            "fair_value_range": {"low": money(fvr.get("low"), cur), "high": money(fvr.get("high"), cur)},
            "upside_pct": wa.get("upside_pct"), "position": vs.get("position"),
            "data_coverage": norm.get("data_coverage"), "available_agent_count": norm.get("available_agent_count"),
        },
        "financial_summary": norm.get("financial_summary"),
        "analyst_summary": norm.get("analyst_summary"),
        "news_summary": norm.get("news_summary"),
        "industry_summary": norm.get("industry_summary"),
        "macro_summary": norm.get("macro_summary"),
        "valuation_summary": vs,
        "scenarios": scen,
    }
    out = fd / f"integrated_{a.date}_{a.company}.json"
    out.write_text(json.dumps(integrated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {out}", file=sys.stderr)
    print(json.dumps({"output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
