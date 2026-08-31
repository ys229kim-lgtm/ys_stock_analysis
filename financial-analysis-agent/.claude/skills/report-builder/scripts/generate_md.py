#!/usr/bin/env python3
"""
generate_md.py — 마크다운 리포트 생성

Usage:
    python generate_md.py \
        --analysis analysis.txt \
        --financials financials.json \
        --charts-dir charts/ \
        --output report.md \
        --date "2026년 6월 2일"
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis",   required=True)
    parser.add_argument("--financials", required=True)
    parser.add_argument("--charts-dir", required=True)
    parser.add_argument("--output",     required=True)
    parser.add_argument("--date",       default=None)
    args = parser.parse_args()

    with open(args.analysis,   encoding="utf-8") as f: analysis = f.read()
    with open(args.financials, encoding="utf-8") as f: fin = json.load(f)

    company  = fin["company"]["name"]
    rtype    = fin["company"].get("report_type", "연결")
    industry = fin["company"].get("industry", "")
    dr       = fin.get("data_range", {})
    start_y  = dr.get("start_year", "")
    end_y    = dr.get("end_year",   "")
    date_str = args.date or datetime.now().strftime("%Y년 %m월 %d일")
    charts   = Path(args.charts_dir)

    def img(filename):
        p = charts / filename
        if p.exists():
            return f"![{filename}](charts/{filename})\n"
        return f"> *(데이터 부족으로 {filename} 미생성)*\n"

    annual = fin.get("annual", [])
    last5  = annual[-5:]

    rows = [
        ("매출액(조원)",     "income_statement", "revenue"),
        ("영업이익(조원)",   "income_statement", "operating_profit"),
        ("영업이익률(%)",    "derived_metrics",  "operating_margin"),
        ("순이익률(%)",      "derived_metrics",  "net_margin"),
        ("ROE(%)",           "derived_metrics",  "roe"),
        ("부채비율(%)",      "derived_metrics",  "debt_ratio"),
        ("이자보상배율(x)",  "derived_metrics",  "interest_coverage"),
        ("FCF(조원)",        "derived_metrics",  "fcf"),
    ]

    header_y = " | ".join(str(a["year"]) for a in last5)
    sep      = "|------|" + "------|" * len(last5)
    table_rows = [f"| 지표 | {header_y} |", sep]
    for label, sec, field in rows:
        vals = []
        for a in last5:
            v = a.get(sec, {}).get(field)
            vals.append(str(round(v, 2)) if v is not None else "N/A")
        table_rows.append(f"| {label} | " + " | ".join(vals) + " |")

    content = f"""# {company} 재무실적 분석 리포트

**분석일자:** {date_str}
**분석 기간:** {start_y}–{end_y}년
**재무제표 기준:** {rtype}
**업종:** {industry}

---

## 목차
1. 기업 개요
2. 수익성 분석
3. 안정성 분석
4. 성장성 분석
5. 현금흐름 분석
6. 수익구조 분석
7. 경쟁사 비교 분석
8. 종합 평가

---

{analysis}

---

## 부록: 주요 재무지표 원본 데이터

{chr(10).join(table_rows)}
"""

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"[OK] 마크다운 리포트 저장: {out}")


if __name__ == "__main__":
    main()
