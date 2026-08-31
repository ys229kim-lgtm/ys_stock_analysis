"""
val_inputs_raw.json을 읽어 파생 지표 계산 및 WACC 산출.
에이전트가 assumptions 섹션을 직접 업데이트한 후 calculate_valuation.py에서 사용.
"""

import argparse
import json
from pathlib import Path
from datetime import date


def compute_derived_financials(raw: dict) -> dict:
    """파생 재무 지표 계산."""
    fin = raw.get("financials", {})
    notes = raw.get("notes", [])

    def safe(v):
        return v if isinstance(v, (int, float)) else None

    revenue = safe(fin.get("revenue_ttm"))
    op_income = safe(fin.get("operating_income_ttm"))
    net_income = safe(fin.get("net_income_ttm"))
    dep = safe(fin.get("depreciation"))
    capex = safe(fin.get("capex"))
    wc_change = safe(fin.get("working_capital_change")) or 0
    net_debt = safe(fin.get("net_debt"))
    total_equity = safe(fin.get("total_equity"))
    shares = safe(fin.get("shares_outstanding"))
    tax_rate = safe(fin.get("effective_tax_rate"))
    ebitda = safe(fin.get("ebitda"))
    bps = safe(fin.get("book_value_per_share"))
    eps = safe(fin.get("eps_ttm"))
    rps = safe(fin.get("revenue_per_share"))

    # EBITDA
    if ebitda is None and op_income is not None and dep is not None:
        ebitda = op_income + dep
        fin["ebitda"] = ebitda
        notes.append("ebitda: 영업이익+D&A 계산")

    # NOPAT
    nopat = None
    if op_income is not None:
        tr = tax_rate if tax_rate else 0.22
        nopat = op_income * (1 - tr)
        if tax_rate is None:
            notes.append(f"nopat: 유효세율 미확인, 22% 가정 적용")

    # FCF
    fcf = None
    if nopat is not None and dep is not None and capex is not None:
        fcf = nopat + dep - capex - wc_change
        notes.append(f"fcf = NOPAT({nopat:.0f}) + D&A({dep:.0f}) - CapEx({capex:.0f}) - 운전자본변동({wc_change:.0f})")
    elif nopat is not None and dep is not None:
        fcf = nopat + dep
        notes.append("fcf: CapEx 미확인, NOPAT+D&A 으로 추정 (과대 추정 가능)")

    # EV 계산용 준비
    market_cap = raw.get("market", {}).get("market_cap")
    ev = None
    if market_cap is not None and net_debt is not None:
        ev = market_cap + net_debt

    # BPS (없으면 계산)
    if bps is None and total_equity is not None and shares is not None and shares > 0:
        bps = total_equity / shares
        fin["book_value_per_share"] = bps
        notes.append("bps: 자본총계/주식수 계산")

    # EPS (없으면 계산)
    if eps is None and net_income is not None and shares is not None and shares > 0:
        eps = net_income / shares
        fin["eps_ttm"] = eps
        notes.append("eps_ttm: 순이익/주식수 계산")

    # RPS (없으면 계산)
    if rps is None and revenue is not None and shares is not None and shares > 0:
        rps = revenue / shares
        fin["revenue_per_share"] = rps
        notes.append("revenue_per_share: 매출/주식수 계산")

    return {
        "nopat": nopat,
        "fcf": fcf,
        "ebitda": ebitda,
        "ev": ev,
    }


def compute_wacc(assumptions: dict, notes: list) -> float | None:
    """CAPM 기반 WACC 계산."""
    rf = assumptions.get("risk_free_rate")
    erp = assumptions.get("market_risk_premium")
    beta = assumptions.get("beta")

    if rf is None or erp is None or beta is None:
        notes.append("wacc: 필수 파라미터 누락 (rf/erp/beta) — 에이전트가 직접 설정 필요")
        return None

    # 순수 자기자본비용 (Ke = Rf + β × ERP)
    ke = rf + beta * erp

    # 단순화: 부채비율 정보 없으면 Ke만으로 WACC 근사
    # (에이전트가 원할 경우 수동으로 부채비율 조정 가능)
    wacc = ke
    notes.append(
        f"wacc: CAPM 기반 Ke={ke:.4f} (Rf={rf}, β={beta}, ERP={erp}). "
        f"부채비율 미반영 — 필요 시 수동 조정."
    )
    return round(wacc, 4)


def build_val_inputs(raw: dict) -> dict:
    today = date.today().strftime("%Y-%m-%d")
    notes = raw.get("notes", [])

    derived = compute_derived_financials(raw)

    # assumptions 초기값 (에이전트가 이후 업데이트)
    assumptions = {
        "risk_free_rate": raw.get("macro", {}).get("risk_free_rate"),
        "market_risk_premium": raw.get("macro", {}).get("market_risk_premium") or 0.055,
        "beta": raw.get("macro", {}).get("beta"),
        "wacc": None,
        "fcf_growth_rate_5y": None,
        "terminal_growth_rate": None,
        "peer_per": raw.get("peer_multiples", {}).get("peer_per"),
        "peer_pbr": raw.get("peer_multiples", {}).get("peer_pbr"),
        "peer_psr": raw.get("peer_multiples", {}).get("peer_psr"),
        "peer_ev_ebitda": raw.get("peer_multiples", {}).get("peer_ev_ebitda"),
    }

    wacc = compute_wacc(assumptions, notes)
    if wacc:
        assumptions["wacc"] = wacc

    # FCF 성장률: 콘센서스 우선
    consensus = raw.get("consensus", {})
    if consensus.get("fcf_growth_from_consensus"):
        assumptions["fcf_growth_rate_5y"] = consensus["fcf_growth_from_consensus"]
        notes.append("fcf_growth_rate_5y: 콘센서스 EPS CAGR 사용")
    else:
        notes.append("fcf_growth_rate_5y: 콘센서스 없음 — 에이전트가 직접 DART FCF 추세 분석 후 설정 필요")

    return {
        "company": raw.get("company"),
        "ticker": raw.get("ticker"),
        "base_date": raw.get("base_date", today),
        "industry_tag": raw.get("industry_tag"),
        "weight_rationale": "",
        "valuation_weights": {
            "dcf_rim": None,
            "relative": None,
            "ddm": None,
        },
        "current_price": raw.get("current_price"),
        "data_sources": raw.get("data_sources", {}),
        "financials": {
            **raw.get("financials", {}),
            "nopat": derived.get("nopat"),
            "fcf": derived.get("fcf"),
            "ebitda": derived.get("ebitda") or raw.get("financials", {}).get("ebitda"),
            "ev": derived.get("ev"),
        },
        "consensus": consensus,
        "assumptions": assumptions,
        "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-inputs", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.raw_inputs, encoding="utf-8") as f:
        raw = json.load(f)

    val_inputs = build_val_inputs(raw)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(val_inputs, f, ensure_ascii=False, indent=2)

    print(f"[OK] val_inputs 저장: {out_path}")

    wacc = val_inputs["assumptions"].get("wacc")
    if wacc:
        print(f"[OK] WACC 계산: {wacc:.2%}")
    else:
        print("[WARN] WACC 미산출 — 에이전트가 assumptions 섹션 수동 설정 필요")

    need_manual = []
    if val_inputs["assumptions"].get("fcf_growth_rate_5y") is None:
        need_manual.append("fcf_growth_rate_5y")
    if val_inputs["assumptions"].get("terminal_growth_rate") is None:
        need_manual.append("terminal_growth_rate")
    if val_inputs["valuation_weights"]["dcf_rim"] is None:
        need_manual.append("valuation_weights")
    if need_manual:
        print(f"[ACTION] 에이전트가 직접 설정 필요: {need_manual}")


if __name__ == "__main__":
    main()
