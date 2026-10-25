#!/usr/bin/env python3
"""
SEC EDGAR companyfacts(XBRL) 기반 미국 상장사 재무 수집·지표 산출.

사용:
  SEC_USER_AGENT="Name email" uv run fetch_sec.py --ticker KBH --date 20261025 --output-dir <financial 폴더>

- 표준 라이브러리만 사용 (설치 불필요)
- 금액 단위: USD millions (주당 값은 USD, 주식수는 millions)
- 출력: financials_{date}_{ticker}.json
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_UA = "stock-analysis-agent research (set SEC_USER_AGENT env: Name email)"

# 개념(concept) 우선순위 목록. 앞에서부터 데이터가 있는 첫 개념을 사용.
CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "interest_expense": ["InterestExpense", "InterestExpenseNonoperating"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
           "DepreciationAmortizationAndAccretionNet"],
    "sbc": ["ShareBasedCompensation"],
    "operating_cf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
}
INSTANT = {
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "debt": ["LongTermDebt", "NotesPayable", "DebtLongtermAndShorttermCombinedAmount", "LongTermDebtNoncurrent",
             "SeniorNotes"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "inventory": ["InventoryNet", "InventoryRealEstate", "InventoryFinishedGoodsNetOfReserves"],
}
PER_SHARE = {
    "eps_diluted": ["EarningsPerShareDiluted"],
    "eps_basic": ["EarningsPerShareBasic"],
    "dps": ["CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"],
}
SHARES = ["WeightedAverageNumberOfDilutedSharesOutstanding"]


def http_json(url: str, ua: str):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def d(s):
    return datetime.strptime(s, "%Y-%m-%d")


def dur(e):
    return (d(e["end"]) - d(e["start"])).days if e.get("start") else None


def dedupe_latest(entries):
    """같은 (start,end) 기간은 가장 최근 filed 값만 유지."""
    best = {}
    for e in entries:
        k = (e.get("start"), e["end"])
        if k not in best or e["filed"] > best[k]["filed"]:
            best[k] = e
    return list(best.values())


def get_units(facts, names, unit="USD"):
    """우선순위 개념들을 기간(start,end) 단위로 병합해 entries와 사용 개념명 반환.

    회사가 중간에 XBRL 태그를 바꾸는 경우(예: Revenues -> RevenueFromContract...)가 흔하므로
    첫 개념만 쓰지 않고, 같은 기간은 우선순위가 높은 개념을, 없는 기간은 다음 개념을 채운다.
    """
    gaap = facts.get("us-gaap", {})
    merged, used = {}, []
    for n in names:
        if n in gaap and unit in gaap[n].get("units", {}):
            used.append(n)
            for e in dedupe_latest(gaap[n]["units"][unit]):
                merged.setdefault((e.get("start"), e["end"]), e)
    return list(merged.values()), ("+".join(used) if used else None)


def annual_flow(entries):
    out = {}
    for e in entries:
        if e.get("form", "").startswith("10-K") and e.get("start") and 330 <= dur(e) <= 380:
            out[e["end"]] = e["val"]
    return out


def ytd_flow(entries):
    return [e for e in entries if e.get("form", "").startswith("10-Q") and e.get("start")]


def instants(entries, forms=("10-K", "10-Q")):
    return {e["end"]: e["val"] for e in entries if not e.get("start") and e.get("form", "").startswith(forms)}


def m(v):
    return None if v is None else round(v / 1e6, 2)


def pct(a, b):
    return None if a is None or b in (None, 0) else round(a / b * 100, 2)


def cagr(first, last, years):
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return round(((last / first) ** (1 / years) - 1) * 100, 2)


def ttm_value(annual, entries):
    """TTM = 최근 FY + 최근 누계(YTD) - 전년 동기 누계. 최근 10-Q가 FY 이후가 아니면 FY 값."""
    if not annual:
        return None, None
    last_fy_end = max(annual)
    ytd = ytd_flow(entries)
    cur = [e for e in ytd if e["end"] > last_fy_end]
    if not cur:
        return annual[last_fy_end], last_fy_end
    latest_end = max(e["end"] for e in cur)
    # 같은 종료일 중 가장 긴 기간 = 누계(YTD)
    cur_e = max((e for e in cur if e["end"] == latest_end), key=dur)
    prior_end_target = d(latest_end) - timedelta(days=365)
    prior = [e for e in ytd if abs((d(e["end"]) - prior_end_target).days) <= 10
             and abs(dur(e) - dur(cur_e)) <= 10]
    if not prior:
        return None, None
    prior_e = max(prior, key=lambda e: e["filed"])
    return annual[last_fy_end] + cur_e["val"] - prior_e["val"], latest_end


def quarterly_series(entries, annual, n=8):
    """3개월 단독 분기 + (FY - 9M 누계)로 4Q 역산."""
    q = {}
    for e in entries:
        if e.get("start") and 80 <= dur(e) <= 100 and e.get("form", "").startswith("10-Q"):
            q[e["end"]] = e["val"]
    for fy_end, fy_val in annual.items():
        nine = [e for e in entries if e.get("start") and 250 <= dur(e) <= 290
                and 60 <= (d(fy_end) - d(e["end"])).days <= 120]
        if nine:
            q[fy_end] = round(fy_val - max(nine, key=lambda e: e["filed"])["val"], 2)
    keys = sorted(q)[-n:]
    return {k: q[k] for k in keys}


def build(ticker: str, ua: str):
    tick = http_json("https://www.sec.gov/files/company_tickers.json", ua)
    row = next((v for v in tick.values() if v["ticker"].upper() == ticker.upper()), None)
    if not row:
        raise SystemExit(f"[ERROR] SEC에서 티커를 찾지 못함: {ticker}")
    cik = f"{row['cik_str']:010d}"
    data = http_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", ua)
    facts = data["facts"]
    missing, used, stale = [], {}, []

    # 기준일: 매출/순이익 중 가장 최근 보고 기간 종료일. 이보다 오래 멈춘 개념(태그 변경·폐기)은 stale 처리.
    ref_ends = []
    for names in (CONCEPTS["revenue"], CONCEPTS["net_income"]):
        ent0, _ = get_units(facts, names)
        ref_ends += [e["end"] for e in ent0]
    ref = d(max(ref_ends)) if ref_ends else None

    flows, ttm, quarters = {}, {}, {}
    for key, names in CONCEPTS.items():
        ent, name = get_units(facts, names)
        if not ent:
            missing.append(key)
            continue
        used[key] = name
        ann = annual_flow(ent)
        if not ann:
            missing.append(key)
            continue
        flows[key] = ann
        if ref and d(max(e["end"] for e in ent)) < ref - timedelta(days=200):
            stale.append(key)
            continue
        v, end = ttm_value(ann, ent)
        if v is not None:
            ttm[key] = (v, end)
        if key in ("revenue", "net_income", "operating_income", "gross_profit"):
            quarters[key] = quarterly_series(ent, ann)

    inst = {}
    for key, names in INSTANT.items():
        ent, name = get_units(facts, names)
        if not ent:
            missing.append(key)
            continue
        used[key] = name
        inst[key] = instants(ent)
        if ref and inst[key] and d(max(inst[key])) < ref - timedelta(days=120):
            stale.append(key)

    ps = {}
    for key, names in PER_SHARE.items():
        ent, name = get_units(facts, names, unit="USD/shares")
        if not ent:
            missing.append(key)
            continue
        used[key] = name
        ps[key] = {"annual": annual_flow(ent), "ttm": ttm_value(annual_flow(ent), ent)}
    dei = facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    shares_latest = max(dei, key=lambda e: (e["end"], e["filed"])) if dei else None

    fy_ends = sorted(flows.get("revenue", {}) or flows.get("net_income", {}))
    annual = []
    for i, end in enumerate(fy_ends):
        g = lambda k: flows.get(k, {}).get(end)
        i_ = lambda k: inst.get(k, {}).get(end)
        rev, ni, oi, gp = g("revenue"), g("net_income"), g("operating_income"), g("gross_profit")
        if gp is None and rev is not None and g("cost_of_revenue") is not None:
            gp = rev - g("cost_of_revenue")
        ocf, capex = g("operating_cf"), g("capex")
        eq, debt, cash = i_("equity"), i_("debt"), i_("cash")
        prev_eq = inst.get("equity", {}).get(fy_ends[i - 1]) if i > 0 else None
        avg_eq = (eq + prev_eq) / 2 if eq is not None and prev_eq is not None else eq
        prev_rev = flows.get("revenue", {}).get(fy_ends[i - 1]) if i > 0 else None
        prev_ni = flows.get("net_income", {}).get(fy_ends[i - 1]) if i > 0 else None
        fcf = ocf - capex if ocf is not None and capex is not None else None
        annual.append({
            "fy_end": end,
            "income_statement": {"revenue": m(rev), "gross_profit": m(gp), "operating_income": m(oi),
                                 "net_income": m(ni),
                                 "eps_diluted": ps.get("eps_diluted", {}).get("annual", {}).get(end),
                                 "da": m(g("da"))},
            "balance_sheet": {"total_assets": m(i_("total_assets")), "total_liabilities": m(i_("total_liabilities")),
                              "equity": m(eq), "cash": m(cash), "debt": m(debt), "inventory": m(i_("inventory"))},
            "cash_flow": {"operating_cf": m(ocf), "capex": m(capex), "fcf": m(fcf),
                          "dividends_paid": m(g("dividends_paid")), "buybacks": m(g("buybacks"))},
            "derived": {
                "gross_margin_pct": pct(gp, rev), "operating_margin_pct": pct(oi, rev),
                "net_margin_pct": pct(ni, rev), "roe_pct": pct(ni, avg_eq),
                "debt_to_equity": None if debt is None or not eq else round(debt / eq, 2),
                "net_debt": m(debt - cash) if debt is not None and cash is not None else None,
                "revenue_yoy_pct": pct(rev - prev_rev, prev_rev) if rev is not None and prev_rev else None,
                "net_income_yoy_pct": pct(ni - prev_ni, prev_ni) if ni is not None and prev_ni else None,
                "fcf_margin_pct": pct(fcf, rev),
                "payout_pct": pct(g("dividends_paid"), ni),
            },
        })

    rev_series = [(a["fy_end"], a["income_statement"]["revenue"]) for a in annual if a["income_statement"]["revenue"]]
    growth = {}
    for yrs in (3, 5):
        if len(rev_series) > yrs:
            growth[f"revenue_cagr_{yrs}y_pct"] = cagr(rev_series[-yrs - 1][1], rev_series[-1][1], yrs)

    ttm_out = {k: m(v[0]) for k, v in ttm.items()}
    ttm_out["period_end"] = max((v[1] for v in ttm.values() if v[1]), default=None)
    if "eps_diluted" in ps and ps["eps_diluted"]["ttm"][0] is not None:
        ttm_out["eps_diluted"] = round(ps["eps_diluted"]["ttm"][0], 2)

    latest_bs = {}
    for k, series in inst.items():
        if series and k not in stale:
            e = max(series)
            latest_bs[k] = m(series[e])
            latest_bs[f"{k}_asof"] = e

    equity_latest = latest_bs.get("equity")
    shares_m = round(shares_latest["val"] / 1e6, 3) if shares_latest else None
    return {
        "company": {"ticker": ticker.upper(), "cik": cik, "name": data.get("entityName"),
                    "source": "SEC EDGAR companyfacts (XBRL)"},
        "unit": "USD millions (per-share in USD, shares in millions)",
        "annual": annual,
        "ttm": ttm_out,
        "quarterly": {k: {e: m(v) for e, v in s.items()} for k, s in quarters.items()},
        "latest_balance_sheet": latest_bs,
        "shares_outstanding_m": shares_m,
        "shares_asof": shares_latest["end"] if shares_latest else None,
        "book_value_per_share": round(equity_latest / shares_m, 2) if equity_latest and shares_m else None,
        "growth_rates": growth,
        "concepts_used": used,
        "missing_concepts": sorted(set(missing)),
        "stale_concepts": sorted(set(stale)),
        "notes": ["XBRL 개념 선택은 우선순위 목록 기준. 회사별 사용자 정의 태그(예: 홈빌딩 영업이익)는 누락될 수 있으므로 "
                  "missing_concepts/stale_concepts(최근 기간 데이터 없음)는 실적 발표자료/웹으로 보완할 것.",
                  "TTM = 최근 FY + 최근 YTD - 전년 동기 YTD"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    ua = os.environ.get("SEC_USER_AGENT", DEFAULT_UA)
    if ua == DEFAULT_UA:
        print("[WARN] SEC_USER_AGENT 미설정 - SEC는 연락처 포함 User-Agent를 요구함 (예: Name email)", file=sys.stderr)
    res = build(a.ticker, ua)
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"financials_{a.date}_{a.ticker.upper()}.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p}", file=sys.stderr)
    print(json.dumps({"output": str(p), "missing": res["missing_concepts"], "stale": res["stale_concepts"],
                      "fy_count": len(res["annual"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
