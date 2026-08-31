"""
Step 5: analysis JSON → 마크다운 리포트 생성
Usage: python generate_md.py --json_path ./output/analysis_20260608_삼성전자_반도체.json
                              --out_path ./output/report_20260608_삼성전자_반도체.md
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


def format_probability_table(horizon_data: dict) -> str:
    rows = []
    for scenario_key, label, emoji in [
        ("positive", "Positive", "🟢"),
        ("base", "Base Case", "⚪"),
        ("negative", "Negative", "🔴"),
    ]:
        s = horizon_data.get(scenario_key, {})
        prob = s.get("probability", "N/A")
        conditions = ", ".join(s.get("conditions", []))
        growth = s.get("market_growth_est", "N/A")
        impact = s.get("impact_on_target", "N/A")
        rows.append(f"| {emoji} {label} | {prob} | {conditions} | {growth} | {impact} |")

    table = "| 시나리오 | 확률 | 핵심 조건 | 시장 성장 전망 | 대상 기업 영향 |\n"
    table += "|---------|------|---------|-------------|-------------|\n"
    table += "\n".join(rows)
    return table


def build_value_chain_table(value_chain: list) -> str:
    if not value_chain:
        return "_밸류체인 데이터 없음_"
    rows = ["| 단계 | 주요 플레이어 |", "|------|------------|"]
    for item in value_chain:
        stage = item.get("stage", "")
        players = ", ".join(item.get("players", []))
        rows.append(f"| {stage} | {players} |")
    return "\n".join(rows)


def generate_report(data: dict) -> str:
    company = data.get("company", "")
    industry = data.get("industry", "")
    date = data.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))

    # 데이터 소스 요약
    sources = data.get("data_sources", {})
    source_summary = (
        f"텔레그램 리포트 {sources.get('telegram_reports', 0)}건 · "
        f"웹 기사 {sources.get('web_articles', 0)}건 · "
        f"시장 데이터 {sources.get('market_tickers', 0)}개 기업"
    )

    overview = data.get("overview", {})
    market_size = data.get("market_size", {})
    competition = data.get("competition", {})
    supply_demand = data.get("supply_demand", {})
    global_trends = data.get("global_trends", [])
    regulation = data.get("regulation", {})
    scenarios = data.get("scenarios", {})
    conclusion = data.get("conclusion", {})
    references = data.get("references", [])

    lines = []

    # 표지
    lines += [
        f"# {company} — {industry} 산업 분석 리포트",
        f"",
        f"**분석일자:** {date}  ",
        f"**대상 기업:** {company}  ",
        f"**분석 산업:** {industry}  ",
        f"**데이터 소스:** {source_summary}  ",
        f"",
        "---",
        "",
        "## 목차",
        "1. 산업 개요 및 밸류체인",
        "2. 시장 규모 및 성장률 전망",
        "3. 주요 플레이어 경쟁 구도",
        "4. 수요·공급 사이클 분석",
        "5. 글로벌 트렌드 및 기술 변화",
        "6. 규제 환경",
        "7. 단기(1년) 확률적 방향성 전망",
        "8. 중기(1~3년) 확률적 방향성 전망",
        "9. 종합 평가 및 대상 기업 시사점",
        "- 부록: 참고 자료",
        "",
        "---",
        "",
    ]

    # 1. 산업 개요
    lines += [
        "## 1. 산업 개요 및 밸류체인",
        "",
        overview.get("industry_definition", "_정의 없음_"),
        "",
        "### 밸류체인 구조",
        "",
        build_value_chain_table(overview.get("value_chain", [])),
        "",
        f"**대상 기업 위치:** {overview.get('target_company_position', '_미기재_')}",
        "",
        "---",
        "",
    ]

    # 2. 시장 규모
    cur = market_size.get("current_global", {})
    f1y = market_size.get("forecast_1y", {})
    f3y = market_size.get("forecast_3y", {})
    lines += [
        "## 2. 시장 규모 및 성장률 전망",
        "",
        f"| 구분 | 규모 | 비고 |",
        f"|------|------|------|",
        f"| 현재 글로벌 시장 ({cur.get('year','')}) | {cur.get('value','')} {cur.get('unit','')} | 출처: {market_size.get('source','')} |",
        f"| 단기 전망 ({f1y.get('year','')}) | {f1y.get('value','')} {f1y.get('unit','')} | CAGR: {market_size.get('cagr_1y','')} |",
        f"| 중기 전망 ({f3y.get('year','')}) | {f3y.get('value','')} {f3y.get('unit','')} | CAGR: {market_size.get('cagr_3y','')} |",
        "",
        "---",
        "",
    ]

    # 3. 경쟁 구도
    top_players = competition.get("top_players", [])
    player_rows = "\n".join(
        f"| {p.get('company','')} | {p.get('market_share','')} | {p.get('region','')} |"
        for p in top_players
    )
    lines += [
        "## 3. 주요 플레이어 경쟁 구도",
        "",
        "| 기업 | 점유율 | 지역 |",
        "|------|--------|------|",
        player_rows,
        "",
        f"**대상 기업 포지션:** {competition.get('target_position', '_미기재_')}  ",
        f"**경쟁 강도:** {competition.get('competitive_intensity', '_미기재_')}",
        "",
        "---",
        "",
    ]

    # 4. 수요·공급 사이클
    lines += [
        "## 4. 수요·공급 사이클 분석",
        "",
        f"**현재 사이클 위치:** {supply_demand.get('current_cycle', '_미기재_')}  ",
        f"**재고 수준:** {supply_demand.get('inventory_level', '_미기재_')}  ",
        f"**가격 추이:** {supply_demand.get('price_trend', '_미기재_')}  ",
        f"**단기 반전 가능성:** {supply_demand.get('cycle_reversal_probability_1y', '_미기재_')}",
        "",
        "---",
        "",
    ]

    # 5. 글로벌 트렌드
    trend_list = "\n".join(f"- {t}" for t in global_trends) if global_trends else "_데이터 없음_"
    lines += [
        "## 5. 글로벌 트렌드 및 기술 변화",
        "",
        trend_list,
        "",
        "---",
        "",
    ]

    # 6. 규제 환경
    dom_regs = "\n".join(f"- {r}" for r in regulation.get("domestic", []))
    ovs_regs = "\n".join(f"- {r}" for r in regulation.get("overseas", []))
    lines += [
        "## 6. 규제 환경",
        "",
        "### 국내",
        dom_regs or "_데이터 없음_",
        "",
        "### 해외",
        ovs_regs or "_데이터 없음_",
        "",
        "---",
        "",
    ]

    # 7. 단기 전망
    short = scenarios.get("short_term", {})
    lines += [
        "## 7. 단기(1년) 확률적 방향성 전망",
        "",
        format_probability_table(short),
        "",
        "---",
        "",
    ]

    # 8. 중기 전망
    mid = scenarios.get("mid_term", {})
    direction = scenarios.get("direction_consistency", "")
    lines += [
        "## 8. 중기(1~3년) 확률적 방향성 전망",
        "",
        format_probability_table(mid),
        "",
    ]
    if direction:
        lines += [f"> **단기·중기 방향성:** {direction}", ""]
    lines += ["---", ""]

    # 9. 종합 평가
    lines += [
        "## 9. 종합 평가 및 대상 기업 시사점",
        "",
    ]
    if conclusion:
        lines += [
            f"**① 시장 순풍 vs 역풍**  ",
            conclusion.get("tailwind_headwind", "_분석 없음_"),
            "",
            f"**② 포지셔닝 개선 여지**  ",
            conclusion.get("positioning_improvement", "_분석 없음_"),
            "",
            f"**③ 할인율·멀티플 연결**  ",
            conclusion.get("valuation_linkage", "_분석 없음_"),
            "",
        ]
    else:
        lines += ["_종합 평가 미작성_", ""]

    lines += ["---", ""]

    # 부록
    if references:
        lines += ["## 부록: 참고 자료", ""]
        for ref in references:
            lines.append(f"- {ref}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", required=True)
    parser.add_argument("--out_path", required=True)
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"[generate_md] 파일 없음: {json_path}")
        raise SystemExit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    report = generate_report(data)

    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"[generate_md] 마크다운 리포트 생성: {out_path}")


if __name__ == "__main__":
    main()
