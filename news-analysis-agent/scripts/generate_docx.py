# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""
Word 문서(.docx) 생성 스크립트.
analysis JSON + report MD를 읽어 python-docx로 Word 문서 생성.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Inches
except ImportError:
    print("[ERROR] python-docx가 설치되지 않았습니다. 'pip install python-docx' 실행 후 재시도하세요.", file=sys.stderr)
    sys.exit(1)


# 색상 정의
COLOR_POSITIVE_BG = RGBColor(0xDC, 0xE6, 0xF1)   # 파란 계열 배경
COLOR_NEGATIVE_BG = RGBColor(0xF4, 0xCC, 0xCC)   # 붉은 계열 배경
COLOR_ONGOING_BG  = RGBColor(0xE0, 0x60, 0x60)   # 진한 적색 (ongoing 강조)
COLOR_PLAN_BG     = RGBColor(0xEA, 0xF4, 0xE6)   # 녹색 계열 (미래계획)
COLOR_HEADER_BG   = RGBColor(0x36, 0x4F, 0x6B)   # 헤더 배경
COLOR_HEADER_FG   = RGBColor(0xFF, 0xFF, 0xFF)   # 헤더 텍스트


def set_cell_bg(cell, rgb: RGBColor) -> None:
    """셀 배경색 설정."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None, font_size: int = 10) -> None:
    cell.text = ""
    para = cell.paragraphs[0]
    run = para.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(font_size)
    if color:
        run.font.color.rgb = color


def add_header_row(table, headers: list[str]) -> None:
    row = table.rows[0]
    for i, header in enumerate(headers):
        cell = row.cells[i]
        set_cell_bg(cell, COLOR_HEADER_BG)
        set_cell_text(cell, header, bold=True, color=COLOR_HEADER_FG)


def add_cover_page(doc: Document, company: str, analysis_date: str, article_count: int, period: str) -> None:
    doc.add_paragraph()
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"{company}")
    run.bold = True
    run.font.size = Pt(28)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = subtitle.add_run("뉴스 수집·사건 분석 리포트")
    run2.font.size = Pt(16)
    run2.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    doc.add_paragraph()
    doc.add_paragraph()

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.add_run(f"분석일: {analysis_date}\n수집 기사: {article_count}건\n분석 기간: {period}")

    doc.add_page_break()


def add_event_table(doc: Document, events: list[dict], category_filter: str) -> None:
    filtered = [e for e in events if e.get("category") == category_filter and not e.get("parse_failed")]
    if not filtered:
        doc.add_paragraph("해당 사건 없음.")
        return

    headers = ["날짜", "사건 제목", "소분류", "영향 규모", "지속 여부"]
    table = doc.add_table(rows=1 + len(filtered), cols=len(headers))
    table.style = "Table Grid"
    add_header_row(table, headers)

    is_negative = category_filter == "negative"

    for i, event in enumerate(filtered, start=1):
        row = table.rows[i]
        ongoing = event.get("ongoing", False)

        cells_data = [
            event.get("event_date", ""),
            event.get("summary", event.get("cluster_title", "")),
            event.get("sub_category", ""),
            event.get("impact_magnitude", ""),
            "⚠️ 진행중" if ongoing else "종결",
        ]

        if category_filter == "positive":
            bg = COLOR_POSITIVE_BG
        elif ongoing and is_negative:
            bg = COLOR_ONGOING_BG
        elif is_negative:
            bg = COLOR_NEGATIVE_BG
        else:
            bg = COLOR_PLAN_BG

        for j, text in enumerate(cells_data):
            cell = row.cells[j]
            set_cell_bg(cell, bg)
            text_color = COLOR_HEADER_FG if (ongoing and is_negative) else None
            set_cell_text(cell, text, color=text_color)


def add_timeline_table(doc: Document, events: list[dict]) -> None:
    sorted_events = sorted(
        [e for e in events if not e.get("parse_failed")],
        key=lambda e: e.get("event_date", ""),
    )
    if not sorted_events:
        doc.add_paragraph("사건 데이터 없음.")
        return

    headers = ["날짜", "사건 제목", "구분", "지속 여부"]
    table = doc.add_table(rows=1 + len(sorted_events), cols=len(headers))
    table.style = "Table Grid"
    add_header_row(table, headers)

    category_label = {
        "positive": "긍정",
        "negative": "부정",
        "future_plan": "미래계획",
        "neutral": "중립",
    }

    for i, event in enumerate(sorted_events, start=1):
        row = table.rows[i]
        cat = event.get("category", "")
        ongoing = event.get("ongoing", False)

        cells_data = [
            event.get("event_date", ""),
            event.get("summary", event.get("cluster_title", "")),
            category_label.get(cat, cat),
            "⚠️ 진행중" if ongoing else "-",
        ]

        if cat == "positive":
            bg = COLOR_POSITIVE_BG
        elif cat == "negative" and ongoing:
            bg = COLOR_ONGOING_BG
        elif cat == "negative":
            bg = COLOR_NEGATIVE_BG
        elif cat == "future_plan":
            bg = COLOR_PLAN_BG
        else:
            bg = RGBColor(0xF5, 0xF5, 0xF5)

        for j, text in enumerate(cells_data):
            cell = row.cells[j]
            set_cell_bg(cell, bg)
            text_color = COLOR_HEADER_FG if (cat == "negative" and ongoing) else None
            set_cell_text(cell, text, color=text_color)


def add_future_plan_table(doc: Document, events: list[dict]) -> None:
    plans = [e for e in events if e.get("category") == "future_plan" and not e.get("parse_failed")]
    if not plans:
        doc.add_paragraph("공식 발표된 미래 추진 계획 없음.")
        return

    def plan_sort_key(e: dict) -> str:
        detail = e.get("future_plan_details") or {}
        return detail.get("timeline", "9999")

    plans.sort(key=plan_sort_key)

    headers = ["목표", "시기", "투자금액", "지속 여부"]
    table = doc.add_table(rows=1 + len(plans), cols=len(headers))
    table.style = "Table Grid"
    add_header_row(table, headers)

    for i, event in enumerate(plans, start=1):
        row = table.rows[i]
        detail = event.get("future_plan_details") or {}
        amount = detail.get("investment_amount")
        unit = detail.get("investment_unit", "")
        amount_str = f"{amount:,}{unit}" if amount else "-"
        ongoing = event.get("ongoing", False)

        cells_data = [
            event.get("summary", ""),
            detail.get("timeline", "명시없음"),
            amount_str,
            "⚠️ 진행중" if ongoing else "-",
        ]

        for j, text in enumerate(cells_data):
            cell = row.cells[j]
            set_cell_bg(cell, COLOR_PLAN_BG)
            set_cell_text(cell, text)


def parse_md_sections(md_text: str) -> dict[str, str]:
    """마크다운에서 ## 섹션 파싱."""
    sections: dict[str, str] = {}
    current_key = "intro"
    current_lines: list[str] = []

    for line in md_text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def add_md_section_text(doc: Document, text: str) -> None:
    """마크다운 텍스트를 단락으로 추가 (헤딩 제외, 테이블 제외)."""
    for line in text.splitlines():
        if line.startswith("|") or line.startswith("---"):
            continue
        if not line.strip():
            doc.add_paragraph()
            continue
        if line.startswith("### "):
            p = doc.add_paragraph(line.lstrip("#").strip(), style="Heading 3")
        elif line.startswith("## "):
            continue
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line.lstrip("-* ").strip(), style="List Bullet")
        else:
            clean = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            clean = re.sub(r"\*(.*?)\*", r"\1", clean)
            doc.add_paragraph(clean)


def generate_docx(analysis_path: str, report_md_path: str, output_path: str, company: str) -> None:
    analysis_data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    events: list[dict] = analysis_data.get("events", [])
    analysis_date = analysis_data.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))
    article_count = len(events)

    md_text = Path(report_md_path).read_text(encoding="utf-8") if Path(report_md_path).exists() else ""
    md_sections = parse_md_sections(md_text)

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.font.size = Pt(10)

    dates = [e.get("event_date", "") for e in events if e.get("event_date")]
    period = f"{min(dates)} ~ {max(dates)}" if dates else "N/A"

    add_cover_page(doc, company, analysis_date, article_count, period)

    doc.add_heading("목차", level=1)
    toc_items = [
        "1. 수집 개요",
        "2. 긍정 사건 분석",
        "3. 부정 사건 분석",
        "4. 사건 타임라인",
        "5. 미래 추진 계획",
        "6. 이슈 패턴 및 리스크 평가",
        "7. 종합 평가 및 핵심 인사이트",
    ]
    for item in toc_items:
        doc.add_paragraph(item, style="List Number")
    doc.add_page_break()

    doc.add_heading("1. 수집 개요", level=1)
    overview_text = md_sections.get("1. 수집 개요", "")
    add_md_section_text(doc, overview_text)

    doc.add_heading("2. 긍정 사건 분석", level=1)
    positive_text = md_sections.get("2. 긍정 사건 분석", "")
    add_md_section_text(doc, positive_text)
    doc.add_heading("사건 목록", level=2)
    add_event_table(doc, events, "positive")

    doc.add_heading("3. 부정 사건 분석", level=1)
    negative_text = md_sections.get("3. 부정 사건 분석", "")
    add_md_section_text(doc, negative_text)
    doc.add_heading("사건 목록 (⚠️ 진한 적색: 현재 진행 중인 리스크)", level=2)
    add_event_table(doc, events, "negative")

    doc.add_heading("4. 사건 타임라인", level=1)
    timeline_text = md_sections.get("4. 사건 타임라인", "")
    add_md_section_text(doc, timeline_text)
    doc.add_heading("전체 사건 목록 (날짜순)", level=2)
    add_timeline_table(doc, events)

    doc.add_heading("5. 미래 추진 계획", level=1)
    plan_text = md_sections.get("5. 미래 추진 계획", "")
    add_md_section_text(doc, plan_text)
    doc.add_heading("계획 목록 (시기 오름차순)", level=2)
    add_future_plan_table(doc, events)

    doc.add_heading("6. 이슈 패턴 및 리스크 평가", level=1)
    pattern_text = md_sections.get("6. 이슈 패턴 및 리스크 평가", "")
    add_md_section_text(doc, pattern_text)

    doc.add_heading("7. 종합 평가 및 핵심 인사이트", level=1)
    summary_text = md_sections.get("7. 종합 평가 및 핵심 인사이트", "")
    add_md_section_text(doc, summary_text)

    doc.add_page_break()
    doc.add_heading("부록: 클러스터별 원문 기사 목록", level=1)
    for event in events:
        if event.get("parse_failed"):
            continue
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"[{event.get('cluster_id', '')}] ").bold = True
        p.add_run(event.get("cluster_title", ""))

    doc.save(output_path)
    print(f"[OK] Word 문서 생성 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Word 리포트 생성")
    parser.add_argument("--analysis", required=True, help="analysis JSON 파일 경로")
    parser.add_argument("--report-md", required=True, help="마크다운 리포트 파일 경로")
    parser.add_argument("--output", required=True, help="출력 docx 파일 경로")
    parser.add_argument("--company", required=True, help="기업명")
    args = parser.parse_args()

    if not Path(args.analysis).exists():
        print(f"[ERROR] analysis JSON 없음: {args.analysis}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.report_md).exists():
        print(f"[ERROR] 마크다운 리포트 없음: {args.report_md}", file=sys.stderr)
        sys.exit(1)

    try:
        generate_docx(args.analysis, args.report_md, args.output, args.company)
    except Exception as e:
        print(f"[ERROR] docx 생성 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
