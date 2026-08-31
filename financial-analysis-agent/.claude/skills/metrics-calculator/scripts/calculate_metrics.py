#!/usr/bin/env python3
"""
calculate_metrics.py — 재무 지표 계산 스크립트

DART 정규화 JSON을 입력받아 파생 지표를 계산하고
표준 financials JSON으로 저장한다.

Usage:
    python calculate_metrics.py \
        --input dart_normalized_20260602_삼성전자.json \
        --output ./20260602_삼성전자/financials_20260602_삼성전자.json \
        --company-name 삼성전자
"""

import argparse
import json
import sys
from pathlib import Path


def detect_unit_scale(raw: dict) -> float:
    """XBRL 메타데이터에서 조원 변환 스케일 감지."""
    # `or` 대신 명시적 None 검사 — decimals=0(원 단위)은 falsy라서
    # `or`를 쓰면 억원 기본값으로 흘러가 모든 수치가 10^4배 틀어진다.
    decimals = raw.get("unit_decimals")
    if decimals is None:
        decimals = raw.get("decimals")
    unit_label = str(raw.get("unit_label", ""))

    if decimals is not None:
        # decimals=-8 → 값 단위는 억원 → scale=1e8; 조원=1e12
        scale_in_won = 10 ** (-int(decimals))
        return scale_in_won / 1e12

    if "조" in unit_label:
        return 1.0
    if "억" in unit_label:
        return 1e8 / 1e12
    if "백만" in unit_label or "million" in unit_label.lower():
        return 1e6 / 1e12

    print("[WARN] 단위 자동 감지 실패 — 억원으로 가정합니다.", file=sys.stderr)
    return 1e8 / 1e12


def sdiv(num, den):
    if num is None or den is None or den == 0:
        return None
    return num / den


def calc_yoy(values: list) -> list:
    result = [None]
    for i in range(1, len(values)):
        p, c = values[i - 1], values[i]
        if p is not None and p != 0 and c is not None:
            result.append((c - p) / abs(p) * 100)
        else:
            result.append(None)
    return result


def flag_outliers(values: list, years: list) -> list:
    flags = []
    for i in range(1, len(values)):
        if values[i] is None or values[i - 1] is None or values[i - 1] == 0:
            continue
        rate = (values[i] - values[i - 1]) / abs(values[i - 1]) * 100
        if abs(rate) >= 500:
            flags.append({
                "year": years[i],
                "change_pct": round(rate, 1),
                "note": f"{years[i-1]}→{years[i]} 전년 대비 {rate:+.1f}% 변동 (이상치 플래그)",
            })
    return flags


def calc_cagr(start, end, n) -> float | None:
    if start is None or end is None or start <= 0 or end <= 0 or n <= 0:
        return None
    return ((end / start) ** (1 / n) - 1) * 100


def process_annual(raw_annual: list, scale: float) -> tuple[list, list]:
    """조원 단위 지표를 계산한다.

    반환값 두 번째 항목은 표시용 반올림을 거치지 않은 원본 정밀도 값이다.
    성장률을 반올림된 값(조원 2자리 = 100억 단위)에서 계산하면 이익 규모가
    0.1조 내외인 기업에서 YoY가 수 %p 단위로 왜곡되므로 반드시 이쪽을 쓴다.
    """
    processed = []
    exact = []
    for item in raw_annual:
        def s(val):
            try:
                return round(float(val) * scale, 4) if val is not None else None
            except (TypeError, ValueError):
                return None

        rev   = s(item.get("revenue")        or item.get("매출액"))
        op    = s(item.get("operating_profit") or item.get("영업이익"))
        ni    = s(item.get("net_income")       or item.get("당기순이익"))
        ta    = s(item.get("total_assets")     or item.get("자산총계"))
        te    = s(item.get("total_equity")     or item.get("자본총계"))
        td    = s(item.get("total_debt")       or item.get("부채총계"))
        ca    = s(item.get("current_assets")   or item.get("유동자산"))
        cl    = s(item.get("current_liabilities") or item.get("유동부채"))
        ocf   = s(item.get("operating_cf")    or item.get("영업활동현금흐름"))
        icf   = s(item.get("investing_cf")    or item.get("투자활동현금흐름"))
        ffcf  = s(item.get("financing_cf")    or item.get("재무활동현금흐름"))
        capex = s(item.get("capex")            or item.get("유형자산의취득"))
        intex = s(item.get("interest_expense") or item.get("이자비용"))

        op_m   = sdiv(op, rev)
        net_m  = sdiv(ni, rev)
        roe    = sdiv(ni, te)
        roa    = sdiv(ni, ta)
        dr     = sdiv(td, te) * 100        if sdiv(td, te)  is not None else None
        cr     = sdiv(ca, cl) * 100        if sdiv(ca, cl)  is not None else None
        ic     = sdiv(op, intex)           if intex and intex > 0 else None
        fcf    = (ocf - abs(capex))        if ocf is not None and capex is not None else None
        fcf_m  = sdiv(fcf, rev)

        def pct(v): return round(v * 100, 2) if v is not None else None
        def rnd(v): return round(v, 2)       if v is not None else None

        exact.append({
            "year": item.get("year") or item.get("연도"),
            "revenue": rev,
            "operating_profit": op,
        })

        processed.append({
            "year": item.get("year") or item.get("연도"),
            "income_statement": {
                "revenue":          rnd(rev),
                "operating_profit": rnd(op),
                "net_income":       rnd(ni),
            },
            "balance_sheet": {
                "total_assets":       rnd(ta),
                "total_equity":       rnd(te),
                "total_debt":         rnd(td),
                "current_assets":     rnd(ca),
                "current_liabilities":rnd(cl),
            },
            "cash_flow": {
                "operating_cf":  rnd(ocf),
                "investing_cf":  rnd(icf),
                "financing_cf":  rnd(ffcf),
                "capex":         rnd(capex),
            },
            "derived_metrics": {
                "operating_margin": pct(op_m),
                "net_margin":       pct(net_m),
                "roe":              pct(roe),
                "roa":              pct(roa),
                "debt_ratio":       rnd(dr),
                "current_ratio":    rnd(cr),
                "interest_coverage":rnd(ic),
                "fcf":              rnd(fcf),
                "fcf_margin":       pct(fcf_m),
            },
        })
    return processed, exact


def calc_growth(exact: list) -> dict:
    """성장률은 표시용 반올림 이전의 정밀 값(process_annual의 두 번째 반환값)에서 계산한다."""
    years = [a["year"] for a in exact]
    revs  = [a["revenue"] for a in exact]
    ops   = [a["operating_profit"] for a in exact]

    rev_yoy = calc_yoy(revs)
    op_yoy  = calc_yoy(ops)
    n = len(revs)

    def cagr_n(k):
        if n < k + 1:
            return None
        return calc_cagr(revs[-(k + 1)], revs[-1], k)

    return {
        "years":           years,
        "revenue_yoy":     [round(v, 2) if v is not None else None for v in rev_yoy],
        "op_profit_yoy":   [round(v, 2) if v is not None else None for v in op_yoy],
        "revenue_cagr_3y": round(cagr_n(3),  2) if cagr_n(3)  is not None else None,
        "revenue_cagr_5y": round(cagr_n(5),  2) if cagr_n(5)  is not None else None,
        "revenue_cagr_10y":round(cagr_n(10), 2) if cagr_n(10) is not None else None,
    }


def validate_schema(annual: list) -> list:
    errors = []
    for item in annual:
        yr = item.get("year")
        for f in ("revenue", "operating_profit", "net_income"):
            if item["income_statement"].get(f) is None:
                errors.append(f"[{yr}] income_statement.{f} 누락")
        for f in ("total_assets", "total_debt"):
            if item["balance_sheet"].get(f) is None:
                errors.append(f"[{yr}] balance_sheet.{f} 누락")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",        required=True)
    parser.add_argument("--output",       required=True)
    parser.add_argument("--company-name", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] 입력 파일 없음: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)

    scale = detect_unit_scale(raw)
    annual_raw = raw.get("annual", raw.get("data", []))

    if len(annual_raw) < 5:
        print(f"[WARN] {len(annual_raw)}개년 데이터 (최소 5개년 권장)", file=sys.stderr)

    annual, annual_exact = process_annual(annual_raw, scale)
    by_year = lambda x: x.get("year") or 0
    annual = sorted(annual, key=by_year)
    annual_exact = sorted(annual_exact, key=by_year)
    years  = [a["year"] for a in annual]
    revs   = [a["income_statement"]["revenue"] for a in annual]

    outliers = flag_outliers(revs, years)
    for o in outliers:
        print(f"[WARN] 이상치: {o['note']}", file=sys.stderr)

    errors = validate_schema(annual)
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(2)

    output = {
        "company": {
            "code":        raw.get("company", {}).get("code", ""),
            "name":        raw.get("company", {}).get("name", args.company_name),
            "industry":    raw.get("company", {}).get("industry", ""),
            "report_type": raw.get("company", {}).get("report_type", "연결"),
        },
        "data_range": {
            "start_year": years[0]  if years else None,
            "end_year":   years[-1] if years else None,
            "note":       f"XBRL 수집 가능 구간 ({len(years)}개년)",
        },
        "unit":          "조원",
        "annual":        annual,
        "segments":      raw.get("segments", []),
        "growth_rates":  calc_growth(annual_exact),
        "outlier_flags": outliers,
        "red_flags":     [],
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[OK] financials JSON 저장: {out}")
    print(f"     분석 구간: {output['data_range']['start_year']}–{output['data_range']['end_year']} ({len(annual)}개년)")


if __name__ == "__main__":
    main()
