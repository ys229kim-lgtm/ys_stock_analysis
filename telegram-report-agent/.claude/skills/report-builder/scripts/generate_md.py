"""
마크다운 리포트 생성 스크립트 (Step 6).
LLM이 생성한 종합 분석 텍스트와 analysis JSON을 결합하여 구조화된 .md 파일을 생성한다.
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from statistics import mean


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_price(value) -> str:
    if value is None:
        return "N/A"
    return f"{int(value):,}원"


def investment_opinion_table(reports: list[dict]) -> str:
    counts = defaultdict(int)
    for r in reports:
        op = r.get("investment_opinion", "명시없음") or "명시없음"
        counts[op] += 1

    total = sum(counts.values())
    lines = ["| 투자의견 | 건수 | 비율 |", "|---------|------|------|"]
    for op in ["Buy", "Hold", "Sell", "명시없음"]:
        n = counts.get(op, 0)
        pct = f"{n/total*100:.0f}%" if total > 0 else "0%"
        lines.append(f"| {op} | {n} | {pct} |")
    lines.append(f"| **합계** | **{total}** | **100%** |")
    return "\n".join(lines)


def target_price_summary(reports: list[dict]) -> str:
    prices = [r["target_price"] for r in reports if r.get("target_price") is not None]
    if not prices:
        return "목표주가 데이터 없음"
    return (
        f"최소 {format_price(min(prices))} / "
        f"평균 {format_price(int(mean(prices)))} / "
        f"최대 {format_price(max(prices))}"
    )


def channel_format_table(meta: dict) -> str:
    by_channel = meta.get("by_channel", {})
    by_format = meta.get("by_format", {})

    lines = ["**채널별 수집:**\n", "| 채널 | 건수 |", "|------|------|"]
    for ch, n in sorted(by_channel.items(), key=lambda x: -x[1]):
        lines.append(f"| {ch} | {n} |")

    lines += ["\n**형식별 수집:**\n", "| 형식 | 건수 |", "|------|------|"]
    for fmt, n in sorted(by_format.items(), key=lambda x: -x[1]):
        lines.append(f"| {fmt.upper()} | {n} |")

    return "\n".join(lines)


def appendix_table(reports: list[dict]) -> str:
    lines = [
        "| 증권사 | 날짜 | 투자의견 | 목표주가 | 채널 |",
        "|--------|------|---------|---------|------|",
    ]
    for r in sorted(reports, key=lambda x: x.get("report_date", ""), reverse=True):
        firm = r.get("securities_firm") or "미상"
        date = r.get("report_date", "")
        op = r.get("investment_opinion", "명시없음")
        tp = format_price(r.get("target_price"))
        ch = r.get("channel", "")
        lines.append(f"| {firm} | {date} | {op} | {tp} | {ch} |")
    return "\n".join(lines)


def build_markdown(
    company: str,
    date: str,
    meta: dict,
    analysis: dict,
    synthesis_text: str,
) -> str:
    reports = [
        r for r in analysis.get("reports", [])
        if not r.get("irrelevant") and not r.get("parse_failed")
    ]
    total_raw = meta.get("total_collected", 0)
    after_dedup = meta.get("after_dedup", 0)
    date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

    period_from = meta.get("period", {}).get("from", "")
    period_to = meta.get("period", {}).get("to", date_fmt)
    period_str = f"{period_from} ~ {period_to}" if period_from else f"~ {period_to}"

    md = f"""# {company} 증권사 리포트 분석

**분석일자:** {date_fmt}
**수집 리포트 수:** {after_dedup}건 (원본 {total_raw}건)
**수집 기간:** {period_str}

---

## 목차

1. 수집 개요
2. 투자의견 분포
3. 긍정 논거 통합
4. 부정 논거 통합
5. 실적 전망 컨센서스
6. Best Case 시나리오
7. Worst Case 시나리오
8. 종합 시각 요약
- 부록: 리포트별 분석 상세

---

## 1. 수집 개요

{channel_format_table(meta)}

- 추출 성공: {meta.get('extraction_success', 0)}건 / {after_dedup}건
- 유효 분석: {len(reports)}건 (irrelevant/parse_failed 제외)

---

## 2. 투자의견 분포

{investment_opinion_table(reports)}

**목표주가 범위:** {target_price_summary(reports)}

---

{synthesis_text}

---

## 부록: 리포트별 분석 상세

{appendix_table(reports)}
"""
    return md


def main():
    parser = argparse.ArgumentParser(description="마크다운 리포트 생성")
    parser.add_argument("--analysis-json", required=True)
    parser.add_argument("--synthesis-text", required=True, help="Step 5 종합 분석 텍스트 파일")
    parser.add_argument("--meta-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    analysis = load_json(Path(args.analysis_json))
    meta = load_json(Path(args.meta_json))
    synthesis_text = Path(args.synthesis_text).read_text(encoding="utf-8")

    md_content = build_markdown(args.company, args.date, meta, analysis, synthesis_text)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"report_{args.date}_{args.company}.md"
    md_path.write_text(md_content, encoding="utf-8")

    print(f"[generate_md] 마크다운 저장: {md_path}")


if __name__ == "__main__":
    main()
