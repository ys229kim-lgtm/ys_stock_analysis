#!/usr/bin/env python3
"""
시나리오(Positive/Base/Negative) 확률 보정 검증 + 주가 범위 산출. 규칙 위반 시 오류로 중단.

규칙 (한국 final-report-agent와 동일):
  - 앵커 확률: 산업 에이전트 값, 없으면 기본 30/50/20
  - 각 시나리오 보정은 앵커 대비 +-15%p 이내, 합계 100%, 보정마다 근거(signal) 필수
  - Positive 범위 = [fair_value_high, 애널리스트 최고 목표가]
    Base      = [fair_value_low, fair_value_high]
    Negative  = [negative_floor, fair_value_low]   (negative_floor = 합리적 하방, 근거 필수)
  - 현재가 > fair_value_high 이면 "모든 시나리오 하방 압력" 플래그

사용:
  uv run build_scenarios.py --val-results val_results.json --tp-high 70 --negative-floor 34 \
     --negative-basis "Argus 최저 목표가" --adjustments adjustments.json --output scenarios.json [--anchor 0.30,0.50,0.20]

adjustments.json 예시 (target 은 positive|base|negative, delta_pp 합계는 0 이어야 함):
  [{"signal": "컨센서스 목표가 연속 하향", "target": "positive", "delta_pp": -3},
   {"signal": "Positive 감소분 배분", "target": "negative", "delta_pp": 3}]
"""
import argparse
import json
import sys
from pathlib import Path

NAMES = ("positive", "base", "negative")


def fail(msg):
    sys.exit(f"[ERROR] {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-results", required=True)
    ap.add_argument("--tp-high", type=float, required=True, help="애널리스트 최고 목표가 (Positive 상단)")
    ap.add_argument("--negative-floor", type=float, required=True, help="Negative 하단 (합리적 하방)")
    ap.add_argument("--negative-basis", required=True, help="Negative 하단 근거")
    ap.add_argument("--anchor", default="0.30,0.50,0.20", help="positive,base,negative 앵커 확률")
    ap.add_argument("--anchor-source", default="default (industry agent 없음)")
    ap.add_argument("--adjustments", help="보정 JSON 파일 경로 (없으면 보정 없음)")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    val = json.loads(Path(a.val_results).read_text(encoding="utf-8"))
    price = val["current_price"]
    fv = val["fair_value_range"]
    lo, hi = fv["low"], fv["high"]

    anchor_vals = [float(x) for x in a.anchor.split(",")]
    if len(anchor_vals) != 3 or abs(sum(anchor_vals) - 1) > 1e-6:
        fail(f"anchor 합계 != 1: {anchor_vals}")
    prob = dict(zip(NAMES, anchor_vals))

    adjustments = json.loads(Path(a.adjustments).read_text(encoding="utf-8")) if a.adjustments else []
    delta = {n: 0.0 for n in NAMES}
    for adj in adjustments:
        if adj.get("target") not in NAMES:
            fail(f"target 오류: {adj}")
        if not str(adj.get("signal", "")).strip():
            fail(f"근거(signal) 없는 보정 금지: {adj}")
        delta[adj["target"]] += float(adj["delta_pp"])
    if abs(sum(delta.values())) > 1e-9:
        fail(f"보정 합계가 0이 아님(확률 합 != 100%): {delta}")
    for n in NAMES:
        if abs(delta[n]) > 15 + 1e-9:
            fail(f"{n} 보정 {delta[n]:+.1f}%p 가 +-15%p 한도 초과")
        prob[n] = round(prob[n] + delta[n] / 100, 4)
        if prob[n] < 0:
            fail(f"{n} 확률 음수")
    if abs(sum(prob.values()) - 1) > 1e-6:
        fail(f"최종 확률 합계 != 1: {prob}")

    flags = []
    pos_lo, pos_hi = hi, a.tp_high
    if a.tp_high <= hi:
        flags.append("tp_high <= fair_value_high: Positive 상단이 적정 범위 상단 이하 -> 상단을 fair_value_high x 1.10 으로 대체")
        pos_hi = round(hi * 1.10, 2)
    if a.negative_floor >= lo:
        fail(f"negative_floor({a.negative_floor}) >= fair_value_low({lo})")
    if price > hi:
        flags.append("현재 주가 고평가 구간 - 모든 시나리오에서 하방 압력")

    rng = {"positive": (pos_lo, pos_hi), "base": (lo, hi), "negative": (a.negative_floor, lo)}
    pct = lambda p: round((p / price - 1) * 100, 1)
    scenarios = {n: {"probability": prob[n], "price_low": round(rng[n][0], 2), "price_high": round(rng[n][1], 2),
                     "vs_current_pct": [pct(rng[n][0]), pct(rng[n][1])]} for n in NAMES}
    wref = round(sum(prob[n] * (rng[n][0] + rng[n][1]) / 2 for n in NAMES), 2)

    res = {
        "currency": val.get("currency", "USD"), "current_price": price, "fair_value_range": fv,
        "price_position": val.get("position"),
        "probability_anchor": {"source": a.anchor_source, **dict(zip(NAMES, anchor_vals))},
        "adjustments": adjustments, "net_adjustment_pp": delta,
        "negative_floor_basis": a.negative_basis, "scenarios": scenarios,
        "probability_weighted_reference": wref, "probability_weighted_vs_current_pct": pct(wref),
        "flags": flags,
    }
    p = Path(a.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p}", file=sys.stderr)
    print(json.dumps({"probs": prob, "ranges": {n: rng[n] for n in NAMES}, "weighted_ref": wref, "flags": flags},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
