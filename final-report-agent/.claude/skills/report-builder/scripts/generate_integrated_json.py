#!/usr/bin/env python3
"""
Step 7-1: 통합 JSON 생성
normalized_summary.json + 시나리오 결과 → integrated_{날짜}_{기업명}.json
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="통합 JSON 생성")
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--final-path", required=True)
    args = parser.parse_args()

    final_dir = Path(args.final_path)

    # normalized_summary.json 로딩
    norm_path = final_dir / "normalized_summary.json"
    if not norm_path.exists():
        print(f"[ERROR] normalized_summary.json 없음: {norm_path}", file=sys.stderr)
        sys.exit(1)

    with open(norm_path, encoding="utf-8") as f:
        normalized = json.load(f)

    # scenarios.json 로딩 (에이전트가 Step 4에서 저장한 시나리오 결과)
    scenario_path = final_dir / "scenarios.json"
    scenarios = {}
    if scenario_path.exists():
        try:
            with open(scenario_path, encoding="utf-8") as f:
                scenarios = json.load(f)
        except Exception as e:
            print(f"[WARN] scenarios.json 로딩 실패: {e}", file=sys.stderr)

    # 통합 JSON 구성
    integrated = {
        "meta": {
            "company": args.company,
            "analysis_date": args.date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent_version": "final-report-agent v1.0",
        },
        "summary": {
            "company": normalized.get("company"),
            "analysis_date": normalized.get("analysis_date"),
            "current_price": normalized.get("current_price"),
            "weighted_avg_fair_value": normalized.get("valuation_summary", {}).get("weighted_avg_fair_value"),
            "fair_value_range": normalized.get("valuation_summary", {}).get("fair_value_range"),
            "upside_pct": normalized.get("valuation_summary", {}).get("upside_pct"),
            "data_coverage": normalized.get("data_coverage"),
            "available_agent_count": normalized.get("available_agent_count"),
        },
        "dart_summary": normalized.get("dart_summary"),
        "telegram_summary": normalized.get("telegram_summary"),
        "news_summary": normalized.get("news_summary"),
        "industry_summary": normalized.get("industry_summary"),
        "valuation_summary": normalized.get("valuation_summary"),
        "scenarios": scenarios,
    }

    out_path = final_dir / f"integrated_{args.date}_{args.company}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(integrated, f, ensure_ascii=False, indent=2)

    print(f"[OK] 통합 JSON 저장: {out_path}", file=sys.stderr)
    print(json.dumps({"output": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
