"""
5종 밸류에이션 계산: DCF, PER/PBR/PSR, EV/EBITDA, DDM(조건부), RIM
val_inputs.json을 읽어 val_results.json 출력.
"""

import argparse
import json
import math
from pathlib import Path
from datetime import date


SENSITIVITY_RANGE = 0.10  # 상단/하단 ±10% 민감도


def safe(v, default=None):
    return v if isinstance(v, (int, float)) and not math.isnan(v) else default


def upside_pct(fair: float, current: float) -> float:
    if not current or current == 0:
        return 0.0
    return round((fair - current) / current * 100, 1)


def calc_dcf(fin: dict, assumptions: dict) -> dict | None:
    """
    DCF 절대가치 평가.
    FCF × (1+g)^t 5년 + 영구성장가치 / WACC-g
    주당 가치 = (NPV + 현금 - 순부채) / 주식수
    """
    fcf = safe(fin.get("fcf"))
    wacc = safe(assumptions.get("wacc"))
    g5 = safe(assumptions.get("fcf_growth_rate_5y"))
    g_term = safe(assumptions.get("terminal_growth_rate"))
    shares = safe(fin.get("shares_outstanding"))
    net_debt = safe(fin.get("net_debt"), 0)
    cash = safe(fin.get("cash"), 0)

    if any(v is None for v in [fcf, wacc, g5, g_term, shares]):
        return None
    if shares <= 0 or wacc <= g_term:
        return None

    # 5년 FCF 현재가치
    pv_fcf = 0
    current_fcf = fcf
    for t in range(1, 6):
        current_fcf *= (1 + g5)
        pv_fcf += current_fcf / (1 + wacc) ** t

    # 영구가치 (5년 후 FCF 기준 Gordon Growth)
    terminal_fcf = current_fcf * (1 + g_term)
    terminal_value = terminal_fcf / (wacc - g_term)
    pv_terminal = terminal_value / (1 + wacc) ** 5

    ev_intrinsic = pv_fcf + pv_terminal
    equity_value = ev_intrinsic - net_debt + cash
    per_share = equity_value / shares

    if per_share <= 0:
        return None

    mid = round(per_share)
    low = round(per_share * (1 - SENSITIVITY_RANGE))
    high = round(per_share * (1 + SENSITIVITY_RANGE))

    return {
        "method": "DCF",
        "low": low, "mid": mid, "high": high,
        "applied_wacc": wacc,
        "applied_growth_5y": g5,
        "applied_terminal_growth": g_term,
    }


def calc_per(fin: dict, assumptions: dict) -> dict | None:
    """PER = peer_per × EPS."""
    eps = safe(fin.get("eps_ttm"))
    peer_per = safe(assumptions.get("peer_per"))
    if eps is None or peer_per is None or eps <= 0:
        return None

    mid = round(peer_per * eps)
    low = round(peer_per * eps * (1 - SENSITIVITY_RANGE))
    high = round(peer_per * eps * (1 + SENSITIVITY_RANGE))

    return {
        "method": "PER",
        "low": low, "mid": mid, "high": high,
        "applied_peer_per": peer_per,
        "applied_eps": eps,
    }


def calc_pbr(fin: dict, assumptions: dict) -> dict | None:
    """PBR = peer_pbr × BPS."""
    bps = safe(fin.get("book_value_per_share"))
    peer_pbr = safe(assumptions.get("peer_pbr"))
    if bps is None or peer_pbr is None or bps <= 0:
        return None

    mid = round(peer_pbr * bps)
    low = round(peer_pbr * bps * (1 - SENSITIVITY_RANGE))
    high = round(peer_pbr * bps * (1 + SENSITIVITY_RANGE))

    return {
        "method": "PBR",
        "low": low, "mid": mid, "high": high,
        "applied_peer_pbr": peer_pbr,
        "applied_bps": bps,
    }


def calc_psr(fin: dict, assumptions: dict) -> dict | None:
    """PSR = peer_psr × 주당매출."""
    rps = safe(fin.get("revenue_per_share"))
    peer_psr = safe(assumptions.get("peer_psr"))
    if rps is None or peer_psr is None or rps <= 0:
        return None

    mid = round(peer_psr * rps)
    low = round(peer_psr * rps * (1 - SENSITIVITY_RANGE))
    high = round(peer_psr * rps * (1 + SENSITIVITY_RANGE))

    return {
        "method": "PSR",
        "low": low, "mid": mid, "high": high,
        "applied_peer_psr": peer_psr,
        "applied_rps": rps,
    }


def calc_ev_ebitda(fin: dict, assumptions: dict) -> dict | None:
    """EV/EBITDA = (peer_ev_ebitda × EBITDA - 순부채) / 주식수."""
    ebitda = safe(fin.get("ebitda"))
    peer_ev_ebitda = safe(assumptions.get("peer_ev_ebitda"))
    net_debt = safe(fin.get("net_debt"), 0)
    shares = safe(fin.get("shares_outstanding"))

    if any(v is None for v in [ebitda, peer_ev_ebitda, shares]):
        return None
    if shares <= 0 or ebitda <= 0:
        return None

    implied_ev = peer_ev_ebitda * ebitda
    equity_value = implied_ev - net_debt
    per_share = equity_value / shares

    if per_share <= 0:
        return None

    mid = round(per_share)
    low = round(per_share * (1 - SENSITIVITY_RANGE))
    high = round(per_share * (1 + SENSITIVITY_RANGE))

    return {
        "method": "EV/EBITDA",
        "low": low, "mid": mid, "high": high,
        "applied_peer_ev_ebitda": peer_ev_ebitda,
        "applied_ebitda": ebitda,
    }


def check_ddm_eligible(fin: dict, assumptions: dict) -> tuple[bool, str]:
    """DDM 적용 가능 여부 판단."""
    dps = safe(fin.get("dps_last"), 0)
    eps = safe(fin.get("eps_ttm"))
    bps = safe(fin.get("book_value_per_share"))
    wacc = safe(assumptions.get("wacc"))
    ke = wacc  # 단순화: Ke ≈ WACC (부채 없는 경우)

    if not dps or dps <= 0:
        return False, "DPS=0 (배당 없음)"

    if eps and eps > 0:
        payout = dps / eps
        if payout >= 1.0:
            return False, f"배당성향={payout:.0%} ≥ 100% (지속 불가)"

    # ROE vs Ke (RIM 계산 결과 활용 가능하면 대체)
    net_income = safe(fin.get("net_income_ttm"))
    total_equity = safe(fin.get("total_equity"))
    if net_income and total_equity and total_equity > 0 and ke:
        roe = net_income / total_equity
        if roe <= ke:
            return False, f"ROE({roe:.2%}) ≤ Ke({ke:.2%}) — 성장가치 음수"

    return True, "DDM 조건 충족"


def calc_ddm(fin: dict, assumptions: dict) -> dict | None:
    """DDM: P = DPS1 / (Ke - g)."""
    eligible, reason = check_ddm_eligible(fin, assumptions)
    if not eligible:
        return {"method": "DDM", "applied": False, "reason": reason}

    dps = safe(fin.get("dps_last"))
    g_term = safe(assumptions.get("terminal_growth_rate"))
    wacc = safe(assumptions.get("wacc"))
    ke = wacc

    if not all([dps, g_term, ke]) or ke <= g_term:
        return {"method": "DDM", "applied": False, "reason": "입력값 부족"}

    dps1 = dps * (1 + g_term)
    mid = round(dps1 / (ke - g_term))

    if mid <= 0:
        return {"method": "DDM", "applied": False, "reason": "산출가 음수"}

    low = round(mid * (1 - SENSITIVITY_RANGE))
    high = round(mid * (1 + SENSITIVITY_RANGE))

    return {
        "method": "DDM",
        "applied": True,
        "low": low, "mid": mid, "high": high,
        "applied_ke": ke,
        "applied_g": g_term,
        "applied_dps1": round(dps1),
    }


def calc_rim(fin: dict, assumptions: dict) -> dict | None:
    """
    RIM (잔여이익모델): P = BPS + Σ(ROE-Ke)×BPS_t / (1+Ke)^t + 영구 RI
    """
    bps = safe(fin.get("book_value_per_share"))
    eps = safe(fin.get("eps_ttm"))
    wacc = safe(assumptions.get("wacc"))
    g_term = safe(assumptions.get("terminal_growth_rate"))

    if any(v is None for v in [bps, eps, wacc, g_term]):
        return None
    if bps <= 0 or wacc <= g_term:
        return None

    ke = wacc
    total_equity = safe(fin.get("total_equity"))
    net_income = safe(fin.get("net_income_ttm"))

    # ROE 계산
    if total_equity and total_equity > 0 and net_income:
        roe = net_income / total_equity
    else:
        roe = eps / bps if bps > 0 else None

    if roe is None:
        return None

    # 5년 잔여이익 현재가치
    current_bps = bps
    pv_ri = 0
    for t in range(1, 6):
        ri = (roe - ke) * current_bps
        pv_ri += ri / (1 + ke) ** t
        current_bps = current_bps * (1 + (roe * (1 - 0.3)))  # 내부유보 가정

    # 영구 잔여이익 (5년 이후 ROE → 업종 평균으로 수렴 가정)
    fade_roe = (roe + ke) / 2  # fade: ROE와 Ke의 중간
    terminal_ri = (fade_roe - ke) * current_bps
    if ke > g_term:
        pv_terminal_ri = terminal_ri / (ke - g_term) / (1 + ke) ** 5
    else:
        pv_terminal_ri = 0

    intrinsic = bps + pv_ri + pv_terminal_ri

    if intrinsic <= 0:
        return None

    mid = round(intrinsic)
    low = round(intrinsic * (1 - SENSITIVITY_RANGE))
    high = round(intrinsic * (1 + SENSITIVITY_RANGE))

    return {
        "method": "RIM",
        "low": low, "mid": mid, "high": high,
        "applied_roe": round(roe, 4),
        "applied_ke": ke,
        "applied_bps": bps,
    }


def apply_weights(results: dict, weights: dict) -> dict:
    """가중 평균 적정가 계산."""
    dcf_rim_methods = ["dcf", "rim"]
    relative_methods = ["per", "pbr", "psr", "ev_ebitda"]
    ddm_methods = ["ddm"]

    w_dcf_rim = weights.get("dcf_rim", 0)
    w_relative = weights.get("relative", 0)
    w_ddm = weights.get("ddm", 0)

    # DDM 미적용 시 가중치 재배분
    ddm_result = results.get("ddm")
    ddm_applied = ddm_result and ddm_result.get("applied") and ddm_result.get("mid")
    if not ddm_applied and w_ddm > 0:
        extra = w_ddm / 2
        w_dcf_rim += extra
        w_relative += extra
        w_ddm = 0

    def group_avg(method_keys, field):
        vals = [results[k][field] for k in method_keys
                if k in results and results[k] and results[k].get(field)]
        return sum(vals) / len(vals) if vals else None

    # 그룹별 평균
    dcf_rim_mid = group_avg(dcf_rim_methods, "mid")
    relative_mid = group_avg(relative_methods, "mid")
    ddm_mid = results["ddm"]["mid"] if ddm_applied else None

    dcf_rim_low = group_avg(dcf_rim_methods, "low")
    relative_low = group_avg(relative_methods, "low")
    ddm_low = results["ddm"].get("low") if ddm_applied else None

    dcf_rim_high = group_avg(dcf_rim_methods, "high")
    relative_high = group_avg(relative_methods, "high")
    ddm_high = results["ddm"].get("high") if ddm_applied else None

    def weighted(dcf_v, rel_v, ddm_v):
        total = 0
        w_total = 0
        if dcf_v and w_dcf_rim:
            total += dcf_v * w_dcf_rim
            w_total += w_dcf_rim
        if rel_v and w_relative:
            total += rel_v * w_relative
            w_total += w_relative
        if ddm_v and w_ddm:
            total += ddm_v * w_ddm
            w_total += w_ddm
        return round(total / w_total) if w_total else None

    wav_mid = weighted(dcf_rim_mid, relative_mid, ddm_mid)
    wav_low = weighted(dcf_rim_low, relative_low, ddm_low)
    wav_high = weighted(dcf_rim_high, relative_high, ddm_high)

    return {
        "low": wav_low,
        "mid": wav_mid,
        "high": wav_high,
    }


def build_consensus_comparison(val_inputs: dict, wav_mid: float | None) -> dict:
    consensus = val_inputs.get("consensus", {})
    avg_tp = consensus.get("avg_target_price")

    if not consensus.get("available") or not avg_tp:
        return {"available": False, "note": "콘센서스 미수집"}

    gap = None
    if wav_mid and wav_mid > 0:
        gap = round((wav_mid - avg_tp) / avg_tp * 100, 1)

    return {
        "available": True,
        "avg_target_price": avg_tp,
        "llm_mid": wav_mid,
        "gap_pct": gap,
        "note": (
            f"LLM 추정이 콘센서스 대비 {gap:+.1f}%" if gap is not None else ""
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-inputs", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.val_inputs, encoding="utf-8") as f:
        vi = json.load(f)

    fin = vi.get("financials", {})
    assumptions = vi.get("assumptions", {})
    weights = vi.get("valuation_weights", {})
    current_price = vi.get("current_price")

    results = {}

    # DCF
    r = calc_dcf(fin, assumptions)
    results["dcf"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] DCF: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] DCF 계산 실패 (필수 입력값 누락)")

    # PER
    r = calc_per(fin, assumptions)
    results["per"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] PER: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] PER 계산 실패")

    # PBR
    r = calc_pbr(fin, assumptions)
    results["pbr"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] PBR: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] PBR 계산 실패")

    # PSR
    r = calc_psr(fin, assumptions)
    results["psr"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] PSR: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] PSR 계산 실패")

    # EV/EBITDA
    r = calc_ev_ebitda(fin, assumptions)
    results["ev_ebitda"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] EV/EBITDA: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] EV/EBITDA 계산 실패")

    # DDM
    r = calc_ddm(fin, assumptions)
    results["ddm"] = r
    ddm_applied = r and r.get("applied") and r.get("mid")
    if ddm_applied:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] DDM: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        reason = r.get("reason", "입력값 부족") if r else "입력값 부족"
        print(f"[INFO] DDM 미적용: {reason}")

    # RIM
    r = calc_rim(fin, assumptions)
    results["rim"] = r
    if r:
        r["upside_pct"] = upside_pct(r["mid"], current_price)
        print(f"[OK] RIM: {r['low']:,} ~ {r['mid']:,} ~ {r['high']:,}원")
    else:
        print("[WARN] RIM 계산 실패")

    # 성공 방법 수 확인
    success_methods = [k for k, v in results.items()
                       if v and v.get("mid") and k != "ddm"]
    if ddm_applied:
        success_methods.append("ddm")

    print(f"\n[결과] 성공 방법: {len(success_methods)}종 — {success_methods}")

    # 가중 평균
    wav = apply_weights(results, weights)
    if wav.get("mid"):
        wav["upside_pct"] = upside_pct(wav["mid"], current_price)
        print(f"[OK] 가중 평균 적정가: {wav['low']:,} ~ {wav['mid']:,} ~ {wav['high']:,}원 (upside {wav['upside_pct']:+.1f}%)")

    # 콘센서스 비교
    consensus_cmp = build_consensus_comparison(vi, wav.get("mid"))

    output = {
        "company": vi.get("company"),
        "base_date": vi.get("base_date"),
        "current_price": current_price,
        "industry_tag": vi.get("industry_tag"),
        "valuation_weights": weights,
        "weight_rationale": vi.get("weight_rationale", ""),
        "results": results,
        "weighted_avg": wav,
        "ddm_applied": ddm_applied,
        "methods_count": len(success_methods),
        "consensus_comparison": consensus_cmp,
        "generated_at": date.today().strftime("%Y-%m-%d"),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] val_results 저장: {out_path}")


if __name__ == "__main__":
    main()
