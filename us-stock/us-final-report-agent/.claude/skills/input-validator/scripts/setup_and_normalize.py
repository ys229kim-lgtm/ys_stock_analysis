#!/usr/bin/env python3
"""
미국 주식 최종 리포트 Step 0~1: 출력 폴더 생성 + 입력 파일 검증 + normalized_summary.json 생성.

기대 입력 (base-path 하위):
  financial/financials_{date}_{TICKER}.json     (필수, fetch_sec.py 산출 + 에이전트 보완)
  valuation/val_results_{date}_{TICKER}.json    (필수, calculate_valuation.py 산출)
  valuation/val_inputs_{date}_{TICKER}.json     (권장)
  analyst/quote_{date}_{TICKER}.json            (권장, fetch_quote.py)
  analyst/analyst_{date}_{TICKER}.json          (선택, 스키마는 us-analyst-news-agent/CLAUDE.md)
  news/news_{date}_{TICKER}.json                (선택)
  industry/industry_{date}_{TICKER}.json        (선택, 스키마는 us-industry-macro-agent/CLAUDE.md)
  industry/macro_{date}.json                    (선택, fetch_fred.py)

사용:
  uv run setup_and_normalize.py --ticker KBH --company "KB Home" --date 20261025 --base-path C:/claude/stock/US/KBH/20261025
"""
import argparse
import json
import sys
from pathlib import Path


def load(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] JSON 로딩 실패 {p}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--base-path", required=True)
    a = ap.parse_args()

    base, t, dt = Path(a.base_path), a.ticker.upper(), a.date
    for sub in ("financial", "analyst", "news", "industry", "valuation", "final"):
        (base / sub).mkdir(parents=True, exist_ok=True)

    files = {
        "financials": base / "financial" / f"financials_{dt}_{t}.json",
        "val_results": base / "valuation" / f"val_results_{dt}_{t}.json",
        "val_inputs": base / "valuation" / f"val_inputs_{dt}_{t}.json",
        "quote": base / "analyst" / f"quote_{dt}_{t}.json",
        "analyst": base / "analyst" / f"analyst_{dt}_{t}.json",
        "news": base / "news" / f"news_{dt}_{t}.json",
        "industry": base / "industry" / f"industry_{dt}_{t}.json",
        "macro": base / "industry" / f"macro_{dt}.json",
    }
    required = ("financials", "val_results")
    data = {k: load(p) for k, p in files.items()}
    lines = [f"=== 입력 파일 검증 ({a.company} / {t} / {dt}) ===", ""]
    for k, p in files.items():
        mark = "✓" if data[k] is not None else ("✗ [필수]" if k in required else "✗")
        lines.append(f"  {mark} {k}: {p}")
    (base / "final" / "missing_inputs.log").write_text("\n".join(lines), encoding="utf-8")
    missing_req = [k for k in required if data[k] is None]
    if missing_req:
        print("\n".join(lines), file=sys.stderr)
        sys.exit(f"[ERROR] 필수 입력 누락: {missing_req} - 해당 에이전트를 먼저 실행하세요.")

    fin, val = data["financials"], data["val_results"]
    quote, analyst, news, industry, macro = (data[k] for k in ("quote", "analyst", "news", "industry", "macro"))

    coverage = {"financial": True, "valuation": True, "analyst": analyst is not None,
                "news": news is not None, "industry": industry is not None or macro is not None}
    active = sum(coverage.values())

    price = val.get("current_price") or (quote or {}).get("price")
    summary = {
        "company": a.company, "ticker": t, "analysis_date": dt, "currency": val.get("currency", "USD"),
        "current_price": price,
        "quote": {k: (quote or {}).get(k) for k in ("last_trading_date", "week52_high", "week52_low", "ma50", "ma200",
                                                    "return_3m_pct", "return_1y_pct", "avg_volume_20d")},
        "financial_summary": {
            "company_name": fin.get("company", {}).get("name"),
            "latest_fy": fin["annual"][-1] if fin.get("annual") else None,
            "ttm": fin.get("ttm"), "latest_balance_sheet": fin.get("latest_balance_sheet"),
            "growth_rates": fin.get("growth_rates"), "shares_outstanding_m": fin.get("shares_outstanding_m"),
            "book_value_per_share": fin.get("book_value_per_share"),
            "missing_concepts": fin.get("missing_concepts"), "stale_concepts": fin.get("stale_concepts"),
            "supplements": fin.get("supplements"),
        },
        "analyst_summary": analyst, "news_summary": news, "industry_summary": industry,
        "macro_summary": {k: v.get("latest") for k, v in (macro or {}).get("series", {}).items()} if macro else None,
        "valuation_summary": {
            "sector_tag": val.get("sector_tag"), "weights_effective": val.get("weights_effective"),
            "methods": {m: {k: r.get(k) for k in ("low", "mid", "high", "upside_pct")}
                        for m, r in val["results"].items() if r.get("applied")},
            "dropped": val.get("weights_dropped"), "weighted_avg": val["weighted_avg"],
            "fair_value_range": val["fair_value_range"], "position": val.get("position"),
            "dispersion_ratio": val.get("mid_dispersion_ratio"), "flags": val.get("flags"),
            "consensus_comparison": val.get("consensus_comparison"),
        },
        "data_coverage": coverage, "available_agent_count": active,
    }
    out = base / "final" / "normalized_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(lines), file=sys.stderr)
    print(f"[OK] {out} (활성 {active}/5)", file=sys.stderr)
    if active <= 2:
        print("[WARN] 활성 에이전트 2개 이하 - 사용자 에스컬레이션 필요", file=sys.stderr)
    print(json.dumps({"output": str(out), "coverage": coverage, "active": active}, ensure_ascii=False))


if __name__ == "__main__":
    main()
