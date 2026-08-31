"""
val_results.json + disclosures.json + biz_model.json → Markdown 리포트 생성.
"""

import argparse
import json
import os
import glob
from pathlib import Path
from datetime import date


def find_json(directory: str, pattern: str) -> dict | None:
    matches = glob.glob(os.path.join(directory, pattern))
    if not matches:
        return None
    with open(matches[0], encoding="utf-8") as f:
        return json.load(f)


def fmt_price(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{int(v):,}원"
    except Exception:
        return str(v)


def fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def fmt_pct_color_md(v) -> str:
    """Markdown 에서는 색상 불가, 방향 기호로 대체."""
    if v is None:
        return "N/A"
    sign = "▲" if v > 0 else ("▼" if v < 0 else "→")
    return f"{sign} {abs(v):.1f}%"


def section_biz_model(biz: dict) -> str:
    if not biz:
        return "\n## 1. 비즈니스모델 분석\n\n> 비즈니스모델 분석 데이터 없음\n"

    lines = ["\n## 1. 비즈니스모델 분석\n"]

    # Price
    pa = biz.get("price_analysis", {})
    lines.append("### 1-1. Price (가격 결정력)\n")
    lines.append(pa.get("details", "분석 내용 없음"))
    lines.append(f"\n- 가격 결정력: **{pa.get('pricing_power', 'N/A')}**")
    lines.append(f"- ASP 추세: **{pa.get('asp_trend', 'N/A')}**\n")

    # Quantity
    qa = biz.get("quantity_analysis", {})
    lines.append("### 1-2. Quantity (수요량)\n")
    lines.append(qa.get("details", "분석 내용 없음"))
    lines.append(f"\n- 판매량 추세: **{qa.get('volume_trend', 'N/A')}**")
    lines.append(f"- 시장점유율: **{qa.get('market_share', 'N/A')}**\n")

    # Cost
    ca = biz.get("cost_analysis", {})
    lines.append("### 1-3. Cost (비용 구조)\n")
    lines.append(ca.get("details", "분석 내용 없음"))
    lines.append(f"\n- 매출원가율 추세: **{ca.get('gross_margin_trend', 'N/A')}**")
    if ca.get("cogs_pct"):
        lines.append(f"- COGS%: **{ca['cogs_pct']:.1f}%**")
    lines.append("")

    # 강약점
    lines.append("### 1-4. 강점 / 약점\n")
    strengths = biz.get("strengths", [])
    weaknesses = biz.get("weaknesses", [])
    if strengths:
        lines.append("**강점:**")
        for s in strengths:
            lines.append(f"- {s}")
    if weaknesses:
        lines.append("\n**약점:**")
        for w in weaknesses:
            lines.append(f"- {w}")
    lines.append("")

    # Moat
    moat = biz.get("moat", {})
    lines.append("### 1-5. 경제적 해자 (Moat)\n")
    lines.append(f"**종합 등급: {moat.get('overall_grade', 'N/A')}**\n")
    moat_items = [
        ("Network Effect", "network_effect"),
        ("Switching Cost", "switching_cost"),
        ("Cost Advantage", "cost_advantage"),
        ("Intangible Assets", "intangible_assets"),
        ("Efficient Scale", "efficient_scale"),
    ]
    lines.append("| 해자 유형 | 판정 |")
    lines.append("|---------|------|")
    for label, key in moat_items:
        lines.append(f"| {label} | {moat.get(key, 'N/A')} |")
    lines.append("")
    if moat.get("rationale"):
        lines.append(f"> {moat['rationale']}\n")

    return "\n".join(lines)


def section_valuation(val: dict, current_price) -> str:
    if not val:
        return "\n## 2. 밸류에이션 종합\n\n> 밸류에이션 계산 데이터 없음\n"

    lines = ["\n## 2. 밸류에이션 종합\n"]

    results = val.get("results", {})
    wav = val.get("weighted_avg", {})

    # 2-A: 비교 테이블
    lines.append("### 2-A. 5종 적정가 비교\n")
    lines.append("| 방법 | 하단 | 중간 | 상단 | 현재가 대비 |")
    lines.append("|-----|------|------|------|-----------|")

    method_display = {
        "dcf": "DCF",
        "per": "PER",
        "pbr": "PBR",
        "psr": "PSR",
        "ev_ebitda": "EV/EBITDA",
        "ddm": "DDM",
        "rim": "RIM",
    }

    for key, label in method_display.items():
        r = results.get(key)
        if not r:
            continue
        if key == "ddm" and not r.get("applied"):
            lines.append(f"| {label} | — | — | — | 미적용: {r.get('reason', '')} |")
            continue
        if not r.get("mid"):
            continue
        up = fmt_pct_color_md(r.get("upside_pct"))
        lines.append(
            f"| {label} | {fmt_price(r.get('low'))} | **{fmt_price(r.get('mid'))}** | {fmt_price(r.get('high'))} | {up} |"
        )

    if wav.get("mid"):
        up = fmt_pct_color_md(wav.get("upside_pct"))
        lines.append(
            f"| **가중 평균** | **{fmt_price(wav.get('low'))}** | **{fmt_price(wav.get('mid'))}** | **{fmt_price(wav.get('high'))}** | **{up}** |"
        )
    lines.append("")

    # 2-B: 콘센서스 비교
    lines.append("### 2-B. 증권사 콘센서스 vs. LLM 추정\n")
    cmp = val.get("consensus_comparison", {})
    if cmp.get("available"):
        lines.append("| 항목 | 콘센서스 | LLM 추정 | 괴리 |")
        lines.append("|-----|---------|---------|------|")
        lines.append(
            f"| 목표주가 | {fmt_price(cmp.get('avg_target_price'))} "
            f"| {fmt_price(cmp.get('llm_mid'))} "
            f"| {fmt_pct(cmp.get('gap_pct'))} |"
        )
        if cmp.get("note"):
            lines.append(f"\n> {cmp['note']}\n")
    else:
        lines.append("> 콘센서스 미수집\n")
        lines.append("| 항목 | 콘센서스 | LLM 추정 | 괴리 |")
        lines.append("|-----|---------|---------|------|")
        lines.append(f"| 목표주가 | — | {fmt_price(wav.get('mid'))} | — |\n")

    # 2-C: 업종 태그 및 가중치
    lines.append("### 2-C. 업종 태그 및 가중치 근거\n")
    lines.append(f"- **업종 태그:** `{val.get('industry_tag', 'N/A')}`")
    weights = val.get("valuation_weights", {})
    lines.append(f"- **가중치:** DCF·RIM {weights.get('dcf_rim', 'N/A'):.0%} / "
                 f"상대가치 {weights.get('relative', 'N/A'):.0%} / "
                 f"DDM {'적용' if val.get('ddm_applied') else '미적용'} {weights.get('ddm', 0):.0%}")
    rationale = val.get("weight_rationale", "")
    if rationale:
        lines.append(f"\n> {rationale}\n")
    else:
        lines.append("")

    # 2-D: 가중 평균 적정가
    lines.append("### 2-D. 가중 평균 적정가\n")
    lines.append(f"| 구분 | 하단 | **중간** | 상단 |")
    lines.append("|-----|------|--------|------|")
    lines.append(
        f"| 적정가 | {fmt_price(wav.get('low'))} | **{fmt_price(wav.get('mid'))}** | {fmt_price(wav.get('high'))} |"
    )
    lines.append("")

    # 2-E: 종합 평가
    lines.append("### 2-E. 종합 평가\n")
    cp = current_price
    mid = wav.get("mid")
    if cp and mid:
        upside = (mid - cp) / cp * 100
        direction = "저평가" if upside > 0 else "고평가"
        lines.append(
            f"> 현재 주가 **{fmt_price(cp)}**은 5종 밸류에이션 가중 평균 **{fmt_price(mid)}** 대비 "
            f"**{abs(upside):.1f}% {direction}** 구간에 위치합니다.\n"
        )
    else:
        lines.append("> 현재 주가 또는 가중 평균 적정가 산출 불가\n")

    # 2-F: 방법 간 괴리
    lines.append("### 2-F. 방법 간 괴리 분석\n")
    mids = [(label, results[key]["mid"]) for key, label in method_display.items()
            if results.get(key) and results[key].get("mid")]
    if len(mids) >= 2:
        min_m = min(mids, key=lambda x: x[1])
        max_m = max(mids, key=lambda x: x[1])
        spread = (max_m[1] - min_m[1]) / min_m[1] * 100 if min_m[1] else 0
        if spread > 30:
            lines.append(
                f"> 최저({min_m[0]}: {fmt_price(min_m[1])})와 최고({max_m[0]}: {fmt_price(max_m[1])}) 간 "
                f"괴리 **{spread:.1f}%** — 방법론별 가정 차이 또는 자본구조 영향 가능. 아래 상세 검토 권장.\n"
            )
        else:
            lines.append(f"> 방법론 간 추정가 수렴 양호 (최대 괴리: {spread:.1f}%)\n")
    else:
        lines.append("> 충분한 방법 수 없음\n")

    return "\n".join(lines)


def section_disclosures(disc: dict) -> str:
    if not disc:
        return "\n## 3. 공시 이벤트\n\n> 공시 분석 데이터 없음\n"

    lines = ["\n## 3. 공시 이벤트\n"]
    lines.append(
        f"수집 기간: {disc.get('collection_period', {}).get('start', 'N/A')} "
        f"~ {disc.get('collection_period', {}).get('end', 'N/A')} "
        f"| 총 {disc.get('total_count', 0)}건 "
        f"(HIGH: {disc.get('high_count', 0)}, "
        f"MEDIUM: {disc.get('medium_count', 0)}, "
        f"LOW: {disc.get('low_count', 0)})\n"
    )

    # HIGH 이벤트
    lines.append("### 3-1. 주요 공시 (HIGH 중요도)\n")
    high_events = [e for e in disc.get("events", []) if e.get("importance") == "high"]
    if high_events:
        for e in high_events:
            impact_icon = {"positive": "▲", "negative": "▼", "neutral": "→"}.get(
                e.get("valuation_impact"), "?"
            )
            lines.append(f"**{e['date']} | {e['title']}** {impact_icon}")
            lines.append(f"> {e.get('summary', '')}")
            if e.get("impact_note"):
                lines.append(f"> 밸류에이션 영향: {e['impact_note']}")
            lines.append("")
    else:
        lines.append("> 해당 기간 HIGH 중요도 공시 없음\n")

    # 진행 중 이슈
    lines.append("### 3-2. 진행 중 이슈\n")
    ongoing = disc.get("ongoing_issues", [])
    if ongoing:
        for o in ongoing:
            lines.append(f"- **{o['title']}** ({o.get('start_date', 'N/A')} ~)")
            lines.append(f"  - 현황: {o.get('current_status', 'N/A')}")
            if o.get("next_milestone"):
                lines.append(f"  - 다음 마일스톤: {o['next_milestone']}")
    else:
        lines.append("> 진행 중 이슈 없음\n")
    lines.append("")

    # 향후 일정
    lines.append("### 3-3. 향후 예정 일정\n")
    upcoming = disc.get("upcoming_schedule", [])
    if upcoming:
        for u in upcoming:
            lines.append(f"- {u.get('date', 'N/A')}: {u.get('event', '')}")
    else:
        lines.append("> 확인된 예정 일정 없음\n")
    lines.append("")

    return "\n".join(lines)


def section_summary(analysis_text: str) -> str:
    if analysis_text:
        return f"\n## 4. 종합 투자 관점 요약\n\n{analysis_text}\n"
    return "\n## 4. 종합 투자 관점 요약\n\n> 에이전트 종합 분석 텍스트 없음 — 에이전트가 Step 6에서 직접 작성\n"


def section_appendix(val: dict) -> str:
    if not val:
        return ""
    lines = ["\n---\n\n## 부록: 가정 및 입력값\n"]
    assumptions = val.get("assumptions", {})

    lines.append("### A. WACC 계산\n")
    lines.append("| 항목 | 값 |")
    lines.append("|-----|---|")
    lines.append(f"| 무위험수익률 (Rf) | {assumptions.get('risk_free_rate', 'N/A')} |")
    lines.append(f"| 베타 (β) | {assumptions.get('beta', 'N/A')} |")
    lines.append(f"| 시장위험프리미엄 (ERP) | {assumptions.get('market_risk_premium', 'N/A')} |")
    lines.append(f"| **WACC** | **{assumptions.get('wacc', 'N/A')}** |")
    lines.append("")

    lines.append("### B. 주요 가정\n")
    lines.append("| 항목 | 값 |")
    lines.append("|-----|---|")
    lines.append(f"| FCF 성장률 (5년) | {assumptions.get('fcf_growth_rate_5y', 'N/A')} |")
    lines.append(f"| 영구 성장률 | {assumptions.get('terminal_growth_rate', 'N/A')} |")
    lines.append(f"| Peer PER | {assumptions.get('peer_per', 'N/A')} |")
    lines.append(f"| Peer PBR | {assumptions.get('peer_pbr', 'N/A')} |")
    lines.append(f"| Peer EV/EBITDA | {assumptions.get('peer_ev_ebitda', 'N/A')} |")
    lines.append("")

    lines.append("### C. 데이터 소스\n")
    sources = val.get("data_sources", {})
    for k, v in sources.items():
        if v:
            lines.append(f"- {k}: `{v}`")
    lines.append("")

    return "\n".join(lines)


def generate_markdown(analysis_dir: str, company: str, date_str: str,
                      summary_text: str = "") -> str:
    # JSON 파일 로드
    val = find_json(analysis_dir, f"val_results_{date_str}_{company}.json")
    disc = find_json(analysis_dir, f"disclosures_{date_str}_{company}.json")
    biz = find_json(analysis_dir, f"biz_model_{date_str}_{company}.json")

    current_price = val.get("current_price") if val else None

    # 커버 헤더
    header = (
        f"# {company} 밸류에이션 분석 리포트\n\n"
        f"**작성일:** {date_str} | **분석 기준:** {val.get('base_date', date_str) if val else date_str} | "
        f"**현재 주가:** {fmt_price(current_price)}\n\n"
        "---\n"
    )

    body = (
        header
        + section_biz_model(biz)
        + "\n---\n"
        + section_valuation(val, current_price)
        + "\n---\n"
        + section_disclosures(disc)
        + "\n---\n"
        + section_summary(summary_text)
        + section_appendix(val)
    )

    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--summary-text", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    md = generate_markdown(
        analysis_dir=args.analysis_dir,
        company=args.company,
        date_str=args.date,
        summary_text=args.summary_text,
    )

    out = args.output or os.path.join(
        args.analysis_dir, f"report_{args.date}_{args.company}.md"
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[OK] Markdown 리포트 저장: {out}")


if __name__ == "__main__":
    main()
