#!/usr/bin/env python3
"""
미국 주식 밸류에이션 엔진 (USD, 소수 2자리).

방법: pe(선행/적용 EPS x 멀티플), pb, ps, ev_ebitda, pe_norm(정상화 EPS x 멀티플), dcf, ddm, rim
- 모든 수치 계산은 이 스크립트가 수행한다(LLM 직접 계산 금지).
- 멀티플·성장률·할인율 등 가정은 val_inputs.json의 assumptions에 근거와 함께 기록한다.
- 적용 불가 방법(입력 부족/조건 불충족)은 자동 제외하고 남은 가중치를 재정규화한다.

사용:
  uv run calculate_valuation.py --val-inputs val_inputs_{date}_{ticker}.json --output val_results_{date}_{ticker}.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

METHODS = ["pe", "pb", "ps", "ev_ebitda", "pe_norm", "dcf", "ddm", "rim"]

# 섹터 태그별 기본 가중치 (references/sector_weight_table.md 와 동일하게 유지)
SECTOR_WEIGHTS = {
    "default":                {"pe": .30, "pb": .15, "ev_ebitda": .15, "dcf": .25, "ddm": .05, "rim": .10},
    "growth_tech":            {"pe": .15, "ps": .20, "ev_ebitda": .15, "dcf": .45, "pe_norm": .05},
    "mature_tech":            {"pe": .25, "ps": .05, "ev_ebitda": .20, "dcf": .35, "ddm": .10, "rim": .05},
    "semis_cycle":            {"pe": .15, "pb": .10, "ev_ebitda": .25, "dcf": .25, "pe_norm": .25},
    "bank":                   {"pe": .25, "pb": .35, "ddm": .20, "rim": .20},
    "insurance":              {"pe": .25, "pb": .35, "ddm": .20, "rim": .20},
    "reit":                   {"pe": .15, "pb": .10, "ev_ebitda": .20, "dcf": .25, "ddm": .30},
    "utility":                {"pe": .20, "pb": .10, "ev_ebitda": .20, "dcf": .25, "ddm": .25},
    "energy_cycle":           {"pe": .10, "pb": .10, "ev_ebitda": .30, "pe_norm": .20, "dcf": .25, "ddm": .05},
    "consumer_staples":       {"pe": .25, "ev_ebitda": .15, "dcf": .30, "ddm": .20, "rim": .10},
    "consumer_discretionary": {"pe": .30, "ps": .05, "ev_ebitda": .20, "dcf": .30, "ddm": .05, "rim": .10},
    "homebuilder_cyclical":   {"pe": .35, "pb": .30, "pe_norm": .20, "rim": .15},
    "healthcare_pharma":      {"pe": .25, "ps": .10, "ev_ebitda": .20, "dcf": .35, "ddm": .10},
    "biotech_pipeline":       {"ps": .40, "dcf": .40, "pb": .20},
    "industrial_cyclical":    {"pe": .25, "pb": .05, "ev_ebitda": .25, "pe_norm": .15, "dcf": .25, "ddm": .05},
}

BAND = 0.15  # 멀티플이 스칼라로 주어졌을 때 하단/상단 +-15%


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and not math.isnan(v) else None


def tri(x):
    """스칼라 또는 {low,mid,high} -> (low, mid, high). 스칼라면 +-BAND."""
    if isinstance(x, dict):
        lo, mi, hi = num(x.get("low")), num(x.get("mid")), num(x.get("high"))
        if None in (lo, mi, hi):
            return None
        return lo, mi, hi
    v = num(x)
    return None if v is None else (v * (1 - BAND), v, v * (1 + BAND))


def r2(v):
    return round(v, 2)


def out(method, lo, mi, hi, price, **extra):
    lo, mi, hi = sorted((lo, mi, hi))
    return {"method": method, "applied": True, "low": r2(lo), "mid": r2(mi), "high": r2(hi),
            "upside_pct": r2((mi / price - 1) * 100), **extra}


def skip(method, reason):
    return {"method": method, "applied": False, "reason": reason}


def calc_pe(f, a, price):
    eps, m = num(f.get("eps_for_pe")), tri(a.get("pe"))
    if eps is None or m is None:
        return skip("pe", "eps_for_pe 또는 assumptions.pe 없음")
    if eps <= 0:
        return skip("pe", "EPS <= 0")
    return out("pe", eps * m[0], eps * m[1], eps * m[2], price, eps=eps, eps_basis=f.get("eps_for_pe_basis"),
               multiples=list(map(r2, m)))


def calc_pb(f, a, price):
    b, m = num(f.get("book_value_per_share")), tri(a.get("pb"))
    if b is None or m is None or b <= 0:
        return skip("pb", "BPS 또는 assumptions.pb 없음/비정상")
    return out("pb", b * m[0], b * m[1], b * m[2], price, bps=b, multiples=list(map(r2, m)))


def calc_ps(f, a, price):
    r, m = num(f.get("revenue_per_share")), tri(a.get("ps"))
    if r is None or m is None or r <= 0:
        return skip("ps", "주당매출 또는 assumptions.ps 없음")
    return out("ps", r * m[0], r * m[1], r * m[2], price, rps=r, multiples=list(map(r2, m)))


def calc_ev_ebitda(f, a, price):
    e, nd, sh, m = num(f.get("ebitda")), num(f.get("net_debt")), num(f.get("shares_outstanding")), tri(a.get("ev_ebitda"))
    if None in (e, nd, sh) or m is None or sh <= 0:
        return skip("ev_ebitda", "ebitda/net_debt/shares 또는 assumptions.ev_ebitda 없음")
    if e <= 0:
        return skip("ev_ebitda", "EBITDA <= 0")
    f_ = lambda mult: (mult * e - nd) / sh
    return out("ev_ebitda", f_(m[0]), f_(m[1]), f_(m[2]), price, ebitda=e, net_debt=nd, multiples=list(map(r2, m)))


def calc_pe_norm(f, a, price):
    en = f.get("eps_normalized")
    mult = a.get("pe_normalized_multiple")
    if not isinstance(en, dict) or mult is None:
        return skip("pe_norm", "eps_normalized(low/mid/high) 또는 pe_normalized_multiple 없음")
    mm = tri(mult) if isinstance(mult, dict) else (mult, mult, mult)
    lo, mi, hi = num(en.get("low")), num(en.get("mid")), num(en.get("high"))
    if None in (lo, mi, hi) or None in mm:
        return skip("pe_norm", "정상화 EPS/멀티플 값 부족")
    return out("pe_norm", lo * mm[0], mi * mm[1], hi * mm[2], price, eps_normalized=en, multiple=mult)


def _dcf_value(fcf, wacc, g5, gt, net_debt, shares):
    pv, cur = 0.0, fcf
    for t in range(1, 6):
        cur *= (1 + g5)
        pv += cur / (1 + wacc) ** t
    tv = cur * (1 + gt) / (wacc - gt)
    ev = pv + tv / (1 + wacc) ** 5
    return (ev - net_debt) / shares


def calc_dcf(f, a, price):
    fcf, sh, nd = num(f.get("fcf")), num(f.get("shares_outstanding")), num(f.get("net_debt")) or 0.0
    w, g5, gt = num(a.get("wacc")), num(a.get("fcf_growth_5y")), num(a.get("terminal_growth"))
    if None in (fcf, sh, w, g5, gt) or sh <= 0:
        return skip("dcf", "fcf/shares/wacc/성장률 없음")
    if fcf <= 0:
        return skip("dcf", "FCF <= 0 (DCF 부적합)")
    if w - gt < 0.02:
        return skip("dcf", "WACC - g < 2%p (영구가치 과대)")
    vals = [_dcf_value(fcf, w + dw, g5, gt + dg, nd, sh) for dw in (-0.01, 0, 0.01) for dg in (-0.005, 0, 0.005)]
    base = _dcf_value(fcf, w, g5, gt, nd, sh)
    if base <= 0:
        return skip("dcf", "DCF 주당가치 <= 0")
    return out("dcf", min(vals), base, max(vals), price, wacc=w, growth_5y=g5, terminal_growth=gt,
               note="low/high = WACC +-1%p, g +-0.5%p 격자의 최소/최대")


def calc_ddm(f, a, price):
    dps, ke, g = num(f.get("dps_next")), num(a.get("ke")), num(a.get("ddm_growth"))
    payout = num(f.get("payout_ratio"))
    if None in (dps, ke, g):
        return skip("ddm", "dps_next/ke/ddm_growth 없음")
    if dps <= 0:
        return skip("ddm", "무배당")
    if payout is not None and payout >= 1:
        return skip("ddm", "배당성향 >= 100%")
    if ke - g < 0.02:
        return skip("ddm", "ke - g < 2%p")
    v = lambda gg: dps / (ke - gg)
    return out("ddm", v(g - 0.005), v(g), v(g + 0.005), price, dps_next=dps, ke=ke, g=g,
               note="배당성향이 낮은 기업은 이익 유보분 가치가 누락되어 과소평가 가능")


def _rim(bv0, roe0, roe_lr, payout, ke, years, omega):
    bv, pv, ri = bv0, 0.0, 0.0
    for t in range(1, years + 1):
        roe = roe0 + (roe_lr - roe0) * t / years
        ri = (roe - ke) * bv
        pv += ri / (1 + ke) ** t
        bv += roe * bv * (1 - payout)
    tv = ri * omega / (1 + ke - omega)
    return bv0 + pv + tv / (1 + ke) ** years


def calc_rim(f, a, price):
    bv0, roe0 = num(f.get("book_value_per_share")), num(f.get("roe"))
    ke, roe_lr = num(a.get("ke")), num(a.get("rim_roe_long_run"))
    payout = num(f.get("payout_ratio")) if num(f.get("payout_ratio")) is not None else 0.3
    if None in (bv0, roe0, ke, roe_lr) or bv0 <= 0:
        return skip("rim", "BPS/roe/ke/rim_roe_long_run 없음")
    years, omega = int(a.get("rim_years", 5)), num(a.get("rim_persistence")) or 0.6
    base = _rim(bv0, roe0, roe_lr, payout, ke, years, omega)
    lo = _rim(bv0, roe0, roe_lr, payout, ke + 0.01, years, omega)
    hi = _rim(bv0, roe0, roe_lr, payout, ke - 0.01, years, omega)
    return out("rim", lo, base, hi, price, roe_start=roe0, roe_long_run=roe_lr, ke=ke,
               note="ROE가 장기 ROE로 선형 수렴, 잔여이익 지속계수 omega 적용. low/high = ke +-1%p")


CALC = {"pe": calc_pe, "pb": calc_pb, "ps": calc_ps, "ev_ebitda": calc_ev_ebitda, "pe_norm": calc_pe_norm,
        "dcf": calc_dcf, "ddm": calc_ddm, "rim": calc_rim}


def position(price, lo, hi):
    if price < lo:
        return "저평가"
    if price > hi:
        return "고평가"
    return "적정 범위"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-inputs", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    inp = json.loads(Path(args.val_inputs).read_text(encoding="utf-8"))
    price = num(inp.get("current_price"))
    if not price or price <= 0:
        sys.exit("[ERROR] current_price 필요")
    f, a = inp.get("financials", {}), inp.get("assumptions", {})
    tag = inp.get("sector_tag", "default")
    if tag not in SECTOR_WEIGHTS:
        sys.exit(f"[ERROR] 알 수 없는 sector_tag: {tag} (허용: {', '.join(SECTOR_WEIGHTS)})")

    results = {m: CALC[m](f, a, price) for m in METHODS}
    requested = inp.get("weights") or SECTOR_WEIGHTS[tag]
    if abs(sum(requested.values()) - 1) > 0.011 and inp.get("weights"):
        print(f"[WARN] weights 합계 {sum(requested.values()):.3f} != 1 (자동 재정규화)", file=sys.stderr)

    usable = {m: w for m, w in requested.items() if w > 0 and results.get(m, {}).get("applied")}
    dropped = {m: results[m].get("reason", "미적용") for m, w in requested.items()
               if w > 0 and not results.get(m, {}).get("applied")}
    if len(usable) < 2:
        sys.exit(f"[ERROR] 적용 가능한 방법이 2종 미만: {list(usable)} / 제외: {dropped}")
    tot = sum(usable.values())
    eff = {m: w / tot for m, w in usable.items()}
    wavg = {k: r2(sum(eff[m] * results[m][k] for m in eff)) for k in ("low", "mid", "high")}
    wavg["upside_pct"] = r2((wavg["mid"] / price - 1) * 100)

    mids = [results[m]["mid"] for m in eff]
    disp = r2(max(mids) / min(mids)) if min(mids) > 0 else None
    cons = None
    an = inp.get("analyst") or {}
    if num(an.get("target_avg")):
        cons = {"avg_target": an["target_avg"], "median_target": an.get("target_median"),
                "low_target": an.get("target_low"), "high_target": an.get("target_high"),
                "analyst_count": an.get("count"),
                "model_mid_vs_avg_target_pct": r2((wavg["mid"] / an["target_avg"] - 1) * 100)}

    res = {
        "ticker": inp.get("ticker"), "company": inp.get("company"), "base_date": inp.get("base_date"),
        "currency": inp.get("currency", "USD"), "current_price": price, "sector_tag": tag,
        "weights_requested": requested, "weights_effective": {m: r2(w) for m, w in eff.items()},
        "weights_dropped": dropped, "weight_rationale": inp.get("weight_rationale"),
        "results": results, "weighted_avg": wavg,
        "fair_value_range": {"low": wavg["low"], "high": wavg["high"]},
        "position": position(price, wavg["low"], wavg["high"]),
        "mid_dispersion_ratio": disp,
        "flags": (["method_dispersion_high(>2x)"] if disp and disp > 2 else []),
        "implied_multiples_at_price": {
            "pe": r2(price / f["eps_for_pe"]) if num(f.get("eps_for_pe")) and f["eps_for_pe"] > 0 else None,
            "pb": r2(price / f["book_value_per_share"]) if num(f.get("book_value_per_share")) else None},
        "consensus_comparison": cons,
        "assumptions": a, "financial_inputs": f,
    }
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p}", file=sys.stderr)
    print(json.dumps({"output": str(p), "weighted": wavg, "position": res["position"], "dropped": dropped},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
