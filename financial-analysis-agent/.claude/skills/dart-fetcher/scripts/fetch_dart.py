#!/usr/bin/env python3
"""
fetch_dart.py — DART MCP 응답 정규화 및 저장 도우미

Claude 에이전트가 dart-mcp MCP 도구로 수집한 응답을
calculate_metrics.py 입력 형식으로 정규화하여 저장한다.

Usage:
    python fetch_dart.py --from-mcp-output mcp_response.json \
        --corp-code 005930 --company-name 삼성전자 \
        --output-dir ./20260602_삼성전자/
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def normalize_dart_response(raw: dict, corp_code: str, company_name: str) -> dict:
    """MCP 응답을 calculate_metrics.py 입력 형식으로 정규화."""
    annual_data = (
        raw.get("annual")
        or raw.get("data")
        or raw.get("financial_data")
        or (raw if isinstance(raw, list) else [])
    )

    company_info = raw.get("company", {})

    return {
        "company": {
            "code": corp_code,
            "name": company_name or company_info.get("name", ""),
            "industry": company_info.get("industry", raw.get("industry", "")),
            "report_type": company_info.get("report_type", "연결"),
        },
        "unit_decimals": raw.get("unit_decimals") or raw.get("decimals"),
        "unit_label": raw.get("unit_label") or raw.get("scale_unit", "억원"),
        "annual": annual_data,
        "segments": raw.get("segments", []),
        "source_date": datetime.now().strftime("%Y%m%d"),
    }


def validate_coverage(normalized: dict) -> dict:
    annual = normalized.get("annual", [])
    years = sorted({
        a.get("year") or a.get("연도")
        for a in annual
        if a.get("year") or a.get("연도")
    })

    coverage = {
        "year_count": len(years),
        "years": years,
        "has_income_statement": any(
            a.get("revenue") or a.get("매출액") for a in annual
        ),
        "has_balance_sheet": any(
            a.get("total_assets") or a.get("자산총계") for a in annual
        ),
        "has_cash_flow": any(
            a.get("operating_cf") or a.get("영업활동현금흐름") for a in annual
        ),
        "warnings": [],
    }

    if len(years) < 5:
        coverage["warnings"].append(
            f"데이터 {len(years)}개년 수집됨 (최소 5개년 권장)"
        )
    if not coverage["has_income_statement"]:
        coverage["warnings"].append("포괄손익계산서 데이터 누락")
    if not coverage["has_balance_sheet"]:
        coverage["warnings"].append("재무상태표 데이터 누락")
    if not coverage["has_cash_flow"]:
        coverage["warnings"].append("현금흐름표 데이터 누락 (스킵 후 진행)")

    return coverage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-mcp-output", default=None,
                        help="MCP 응답 JSON 파일 경로 (없으면 stdin)")
    parser.add_argument("--corp-code", required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if args.from_mcp_output:
        with open(args.from_mcp_output, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    normalized = normalize_dart_response(raw, args.corp_code, args.company_name)
    coverage = validate_coverage(normalized)

    for w in coverage["warnings"]:
        print(f"[WARN] {w}", file=sys.stderr)

    if not coverage["has_income_statement"] and not coverage["has_balance_sheet"]:
        print("[ERROR] 재무데이터 수집 실패 — 손익계산서·재무상태표 모두 없음",
              file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"dart_normalized_{date_str}_{args.company_name}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    start = coverage["years"][0] if coverage["years"] else "?"
    end = coverage["years"][-1] if coverage["years"] else "?"
    print(f"[OK] DART 데이터 저장: {output_path}")
    print(f"     수집 기간: {start}–{end} ({coverage['year_count']}개년)")
    print(str(output_path))


if __name__ == "__main__":
    main()
