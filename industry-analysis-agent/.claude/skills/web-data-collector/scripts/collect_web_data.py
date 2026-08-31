"""
Step 3: 웹 검색 + 시장 데이터 수집 결과를 industry_data JSON으로 저장
Usage: python collect_web_data.py --output_path ./output/industry_data_20260608_삼성전자.json
       --company 삼성전자 --industry 반도체 --date 20260608

실제 웹 검색과 MCP 호출은 Claude 에이전트가 수행하고,
이 스크립트는 수집된 데이터를 구조화된 JSON으로 저장한다.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


DOMAIN_KEYS = [
    "overview",       # 산업 개요·밸류체인
    "market_size",    # 시장 규모·성장률
    "competition",    # 경쟁 구도
    "supply_demand",  # 수요·공급 사이클
    "global_trends",  # 글로벌 트렌드·기술
    "regulation",     # 규제 환경
    "outlook",        # 단기·중기 전망
]


def build_empty_structure(company: str, industry: str, date: str) -> dict:
    return {
        "company": company,
        "industry": industry,
        "collection_date": date,
        "web_data": {key: [] for key in DOMAIN_KEYS},
        "market_data": {
            "domestic": [],   # korea-stock-mcp
            "overseas": [],   # yfinance
            "etf": [],        # 산업 ETF
        },
        "coverage_summary": {
            key: "not_collected" for key in DOMAIN_KEYS
        },
    }


def validate_coverage(data: dict) -> dict:
    """7대 영역 중 몇 개 확보했는지 확인."""
    covered = sum(
        1 for key in DOMAIN_KEYS
        if data["web_data"].get(key)
    )
    data["coverage_summary"]["total_covered"] = covered
    data["coverage_summary"]["coverage_rate"] = f"{covered}/{len(DOMAIN_KEYS)}"
    data["coverage_summary"]["meets_threshold"] = covered >= 5
    return data


def save_industry_data(data: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[collect_web_data] 저장 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--industry", required=True)
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--data_json", default="", help="에이전트가 수집한 JSON 문자열 (선택)")
    args = parser.parse_args()

    output_path = Path(args.output_path)

    if args.data_json:
        try:
            data = json.loads(args.data_json)
        except json.JSONDecodeError:
            print("[경고] data_json 파싱 실패, 빈 구조로 초기화합니다.")
            data = build_empty_structure(args.company, args.industry, args.date)
    else:
        data = build_empty_structure(args.company, args.industry, args.date)

    # 필수 필드 보완
    data.setdefault("company", args.company)
    data.setdefault("industry", args.industry)
    data.setdefault("collection_date", args.date)

    data = validate_coverage(data)
    save_industry_data(data, output_path)

    covered = data["coverage_summary"]["total_covered"]
    print(f"  커버리지: {covered}/{len(DOMAIN_KEYS)} 영역")
    if not data["coverage_summary"]["meets_threshold"]:
        print(f"  ⚠️ 5개 영역 미달 — 일부 섹션 '데이터 불충분' 표기 필요")


if __name__ == "__main__":
    main()
