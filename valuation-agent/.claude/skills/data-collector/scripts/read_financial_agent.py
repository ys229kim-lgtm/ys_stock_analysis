"""
선행 에이전트 산출물에서 밸류에이션 입력값 추출.
financial / telegram / industry 에이전트 출력 JSON을 읽어
val_inputs_raw.json 초안 생성.
"""

import argparse
import json
import os
import glob
from pathlib import Path
from datetime import date


def find_json(directory: str, pattern: str) -> dict | None:
    """패턴에 맞는 첫 번째 JSON 파일을 반환."""
    if not directory or not os.path.isdir(directory):
        return None
    matches = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
    if not matches:
        matches = glob.glob(os.path.join(directory, pattern))
    if not matches:
        return None
    with open(matches[0], encoding="utf-8") as f:
        return json.load(f)


def extract_financials(fin_data: dict) -> dict:
    """financial-agent JSON에서 재무 수치 추출."""
    result = {
        "revenue_ttm": None,
        "operating_income_ttm": None,
        "net_income_ttm": None,
        "ebitda": None,
        "depreciation": None,
        "capex": None,
        "working_capital_change": None,
        "net_debt": None,
        "total_equity": None,
        "book_value_per_share": None,
        "eps_ttm": None,
        "dps_last": None,
        "revenue_per_share": None,
        "shares_outstanding": None,
        "effective_tax_rate": None,
    }
    if not fin_data:
        return result

    # financial-agent는 다양한 JSON 구조를 가질 수 있음. 여러 경로 시도.
    def try_get(data, *paths):
        """중첩된 경로에서 값 추출."""
        for path in paths:
            keys = path.split(".")
            v = data
            try:
                for k in keys:
                    v = v[k]
                if v is not None and v not in ("N/A", "XBRL 파싱 오류", "데이터 추출 오류", ""):
                    return v
            except (KeyError, TypeError):
                continue
        return None

    result["revenue_ttm"] = try_get(fin_data,
        "summary.revenue", "financials.revenue", "income_statement.revenue",
        "매출액", "revenue")
    result["operating_income_ttm"] = try_get(fin_data,
        "summary.operating_income", "financials.operating_income",
        "income_statement.operating_income", "영업이익")
    result["net_income_ttm"] = try_get(fin_data,
        "summary.net_income", "financials.net_income",
        "income_statement.net_income", "당기순이익")
    result["ebitda"] = try_get(fin_data,
        "summary.ebitda", "financials.ebitda", "ebitda")
    result["depreciation"] = try_get(fin_data,
        "summary.depreciation", "cash_flow.depreciation",
        "감가상각비", "depreciation_amortization")
    result["capex"] = try_get(fin_data,
        "summary.capex", "cash_flow.capex",
        "설비투자", "capital_expenditure")
    result["working_capital_change"] = try_get(fin_data,
        "cash_flow.working_capital_change", "운전자본변동")
    result["net_debt"] = try_get(fin_data,
        "balance.net_debt", "financials.net_debt", "순차입금")
    result["total_equity"] = try_get(fin_data,
        "balance.total_equity", "financials.total_equity", "자본총계")
    result["book_value_per_share"] = try_get(fin_data,
        "per_share.bps", "per_share.book_value", "BPS", "주당순자산")
    result["eps_ttm"] = try_get(fin_data,
        "per_share.eps_ttm", "per_share.eps", "EPS", "주당순이익")
    result["dps_last"] = try_get(fin_data,
        "per_share.dps", "DPS", "주당배당금")
    result["revenue_per_share"] = try_get(fin_data,
        "per_share.rps", "per_share.revenue", "RPS", "주당매출액")
    result["shares_outstanding"] = try_get(fin_data,
        "shares.total_shares", "shares_outstanding", "발행주식수")
    result["effective_tax_rate"] = try_get(fin_data,
        "income_tax.effective_rate", "tax_rate", "실효세율")

    # EBITDA 없으면 계산
    if result["ebitda"] is None:
        op = result["operating_income_ttm"]
        dep = result["depreciation"]
        if op is not None and dep is not None:
            result["ebitda"] = op + dep
            print("[INFO] EBITDA = 영업이익 + D&A 로 계산")

    return result


def extract_consensus(tele_data: dict) -> dict:
    """telegram-agent JSON에서 콘센서스 데이터 추출."""
    result = {
        "available": False,
        "target_price_list": [],
        "avg_target_price": None,
        "avg_eps_estimate": None,
        "fcf_growth_from_consensus": None,
    }
    if not tele_data:
        return result

    def try_get(data, *paths):
        for path in paths:
            keys = path.split(".")
            v = data
            try:
                for k in keys:
                    v = v[k]
                if v is not None:
                    return v
            except (KeyError, TypeError):
                continue
        return None

    targets = try_get(tele_data,
        "consensus.target_prices", "analysis.target_prices",
        "output.target_price_list", "target_prices")
    if isinstance(targets, list) and len(targets) > 0:
        result["available"] = True
        result["target_price_list"] = targets
        numeric = [t for t in targets if isinstance(t, (int, float))]
        if numeric:
            result["avg_target_price"] = sum(numeric) / len(numeric)

    avg_tp = try_get(tele_data,
        "consensus.avg_target_price", "analysis.avg_target_price", "avg_target_price")
    if avg_tp:
        result["avg_target_price"] = avg_tp
        result["available"] = True

    avg_eps = try_get(tele_data,
        "consensus.avg_eps_estimate", "analysis.avg_eps", "avg_eps_estimate")
    if avg_eps:
        result["avg_eps_estimate"] = avg_eps

    rev_growth = try_get(tele_data,
        "consensus.avg_revenue_growth", "analysis.revenue_growth_estimate")
    if rev_growth:
        result["fcf_growth_from_consensus"] = rev_growth

    return result


def extract_industry_tag(ind_data: dict) -> str | None:
    """industry-agent JSON에서 industry_tag 추출."""
    if not ind_data:
        return None

    def try_get(data, *paths):
        for path in paths:
            keys = path.split(".")
            v = data
            try:
                for k in keys:
                    v = v[k]
                if v:
                    return v
            except (KeyError, TypeError):
                continue
        return None

    return try_get(ind_data,
        "industry_tag", "classification.industry_tag",
        "analysis.industry_tag", "industry_classification.industry_tag")


def build_raw_inputs(
    company: str,
    ticker: str,
    financial_path: str,
    telegram_path: str,
    industry_path: str,
) -> dict:
    today = date.today().strftime("%Y-%m-%d")

    # 각 에이전트 산출물 로드
    fin_json = (
        find_json(financial_path, "analysis_*.json")
        or find_json(financial_path, "financial_*.json")
        or find_json(financial_path, "summary_*.json")
        or find_json(financial_path, "*.json")
    )
    tele_json = (
        find_json(telegram_path, "analysis_*.json")
        or find_json(telegram_path, "*.json")
    )
    ind_json = (
        find_json(industry_path, "analysis_*.json")
        or find_json(industry_path, "industry_classification.json")
        or find_json(industry_path, "*.json")
    )

    if fin_json:
        print(f"[INFO] financial-agent 데이터 로드 완료")
    else:
        print(f"[WARN] financial-agent 데이터 없음: {financial_path}")

    financials = extract_financials(fin_json)
    consensus = extract_consensus(tele_json)
    industry_tag = extract_industry_tag(ind_json)

    missing = [k for k, v in financials.items() if v is None and k not in (
        "depreciation", "capex", "working_capital_change", "dps_last", "revenue_per_share"
    )]

    return {
        "company": company,
        "ticker": ticker,
        "base_date": today,
        "current_price": None,
        "industry_tag": industry_tag,
        "financials": financials,
        "consensus": consensus,
        "market": {
            "market_cap": None,
            "per_exchange": None,
            "pbr_exchange": None,
        },
        "macro": {
            "risk_free_rate": None,
            "market_risk_premium": None,
            "beta": None,
        },
        "peer_multiples": {
            "peer_per": None,
            "peer_pbr": None,
            "peer_psr": None,
            "peer_ev_ebitda": None,
        },
        "data_sources": {
            "financial_agent_path": financial_path,
            "telegram_agent_path": telegram_path,
            "industry_agent_path": industry_path,
        },
        "missing_fields": missing,
        "notes": [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--financial-path", default="")
    parser.add_argument("--telegram-path", default="")
    parser.add_argument("--industry-path", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = build_raw_inputs(
        company=args.company,
        ticker=args.ticker,
        financial_path=args.financial_path,
        telegram_path=args.telegram_path,
        industry_path=args.industry_path,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] val_inputs_raw 저장: {out_path}")
    if data["missing_fields"]:
        print(f"[WARN] 누락 필드 (MCP 보완 필요): {data['missing_fields']}")


if __name__ == "__main__":
    main()
