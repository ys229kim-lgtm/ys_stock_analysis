#!/usr/bin/env python3
"""
Step 7-2: 최종 Markdown 리포트 생성
에이전트가 섹션별로 Append 저장한 report_{날짜}_{기업명}.md에
표지·목차·부록을 추가하여 최종본으로 확정한다.
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


SECTION_HEADERS = [
    "1. 기업 개요 및 데이터 커버리지",
    "2. 비즈니스모델 분석",
    "3. 재무 실적 분석",
    "4. 산업·시장 환경",
    "5. 증권사 리포트·뉴스 종합",
    "6. 밸류에이션 종합",
    "7. 투자 시나리오 및 주가 전망",
]


def build_cover(company: str, date: str, summary: dict) -> str:
    current_price = summary.get("current_price") or "N/A"
    fair_value = summary.get("weighted_avg_fair_value") or "N/A"
    upside = summary.get("upside_pct")
    upside_str = f"{upside:+.1f}%" if isinstance(upside, (int, float)) else "N/A"
    fvr = summary.get("fair_value_range") or {}
    fvr_str = f"{fvr.get('low', 'N/A')}원 ~ {fvr.get('high', 'N/A')}원"

    date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else date

    return f"""---
# {company} 기업분석 종합 리포트

**분석일자:** {date_fmt}
**현재 주가:** {current_price:,}원
**가중 평균 적정가:** {fair_value if isinstance(fair_value, str) else f"{fair_value:,}"}원
**적정가 범위:** {fvr_str}
**Upside/Downside:** {upside_str}

> 본 리포트는 DART 재무분석·증권사 리포트·뉴스·산업 분석·밸류에이션 5개 에이전트 산출물을 종합한 분석 자료입니다.
> 투자 권유가 아닌 분석 정보 제공을 목적으로 합니다. 투자 결정은 투자자 본인의 판단과 책임 하에 이루어져야 합니다.

---
""".replace("{current_price:,}", f"{current_price:,}" if isinstance(current_price, (int, float)) else str(current_price))


def build_toc() -> str:
    lines = ["## 목차\n"]
    lines.append("- [Executive Summary](#executive-summary)")
    for h in SECTION_HEADERS:
        anchor = h.lower().replace(" ", "-").replace("·", "").replace(".", "").replace(",", "")
        lines.append(f"- [{h}](#{anchor})")
    lines.append("- [부록 A: 주요 재무지표 원본 테이블](#부록-a)")
    lines.append("- [부록 B: 밸류에이션 상세 계산](#부록-b)")
    lines.append("- [부록 C: 참고 자료 목록](#부록-c)")
    lines.append("\n---\n")
    return "\n".join(lines)


def build_appendix_placeholder() -> str:
    return """
---

## 부록 A: 주요 재무지표 원본 테이블

> DART 에이전트 산출물(`financials_{날짜}_{기업명}.json`) 원본 데이터 참조

---

## 부록 B: 밸류에이션 상세 계산

> Valuation 에이전트 산출물(`val_inputs_{날짜}_{기업명}.json`, `val_results_{날짜}_{기업명}.json`) 원본 참조

---

## 부록 C: 참고 자료 목록

| 에이전트 | 산출물 경로 |
|---------|-----------|
| DART 재무분석 | `financial/financials_{날짜}_{기업명}.json` |
| 증권사 리포트 | `telegram/analysis_{날짜}_{기업명}.json` |
| 뉴스 분석 | `news/analysis_{날짜}_{기업명}.json` |
| 산업 분석 | `industry/analysis_{날짜}_{기업명}.json` |
| 밸류에이션 | `valuation/val_results_{날짜}_{기업명}.json` |
"""


def main():
    parser = argparse.ArgumentParser(description="최종 Markdown 리포트 생성")
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--final-path", required=True)
    args = parser.parse_args()

    final_dir = Path(args.final_path)
    report_path = final_dir / f"report_{args.date}_{args.company}.md"

    # integrated JSON에서 summary 추출
    integrated_path = final_dir / f"integrated_{args.date}_{args.company}.json"
    summary = {}
    if integrated_path.exists():
        try:
            with open(integrated_path, encoding="utf-8") as f:
                integrated = json.load(f)
            summary = integrated.get("summary", {})
        except Exception as e:
            print(f"[WARN] integrated JSON 로딩 실패: {e}", file=sys.stderr)

    # 기존 report 내용 읽기 (에이전트가 섹션별 Append 저장한 내용)
    existing_content = ""
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            existing_content = f.read()

    # 표지가 이미 있는지 확인
    has_cover = existing_content.strip().startswith("---\n#") or "기업분석 종합 리포트" in existing_content[:200]

    if has_cover:
        # 이미 표지 있으면 그대로 유지, 부록만 추가
        final_content = existing_content
        if "부록 A" not in final_content:
            final_content += build_appendix_placeholder().replace("{날짜}", args.date).replace("{기업명}", args.company)
    else:
        # 표지 + 목차 + 기존 내용 + 부록 조합
        cover = build_cover(args.company, args.date, summary)
        toc = build_toc()
        appendix = build_appendix_placeholder().replace("{날짜}", args.date).replace("{기업명}", args.company)
        final_content = cover + toc + existing_content + appendix

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    size_kb = report_path.stat().st_size // 1024
    print(f"[OK] Markdown 리포트 저장: {report_path} ({size_kb}KB)", file=sys.stderr)
    print(json.dumps({"output": str(report_path), "size_kb": size_kb}, ensure_ascii=False))


if __name__ == "__main__":
    main()
