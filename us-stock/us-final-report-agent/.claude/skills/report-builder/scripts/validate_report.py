#!/usr/bin/env python3
"""
최종 리포트 자기 검증(Step 6) 자동 점검. 실패 항목이 있으면 exit 1.

점검:
  1 섹션 1~7 및 Executive Summary 존재
  2 시나리오 확률 합 100% 및 md 본문 표기와 scenarios.json 일치
  3 시나리오 주가 범위가 md 본문에 표기됨 (scenarios.json 값, $ 소수 2자리)
  4 금지 표현 0건
  5 출처 표기 (← ...) 최소 개수
  6 고평가 특례 문구 (현재가 > 적정 범위 상단일 때)
  7 면책 문구 존재

사용:
  uv run validate_report.py --report report.md --scenarios scenarios.json [--min-sources 20]
"""
import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN = [
    "매수를 권유", "투자를 추천", "사세요", "지금이 매수", "지금 사야", "반드시 매수",
    "손실 위험이 없", "다운사이드 없음", "안전한 투자", "원금 손실 걱정 없이",
    "확실한 수익", "반드시 오릅", "100% 상승", "무조건 수익", "틀림없이",
]
SECTIONS = [r"##\s*1\.\s*기업 개요", r"##\s*2\.\s*비즈니스모델", r"##\s*3\.\s*재무 실적", r"##\s*4\.\s*산업",
            r"##\s*5\.\s*(애널리스트|증권사)", r"##\s*6\.\s*밸류에이션", r"##\s*7\.\s*투자 시나리오"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--scenarios", required=True)
    ap.add_argument("--min-sources", type=int, default=20)
    a = ap.parse_args()

    md = Path(a.report).read_text(encoding="utf-8")
    sc = json.loads(Path(a.scenarios).read_text(encoding="utf-8"))
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    miss = [s for s in SECTIONS if not re.search(s, md)]
    add("섹션 1~7 존재", not miss, f"누락: {miss}" if miss else "")
    add("Executive Summary 존재", "Executive Summary" in md)

    probs = {n: sc["scenarios"][n]["probability"] for n in ("positive", "base", "negative")}
    add("확률 합 100%", abs(sum(probs.values()) - 1) < 1e-6, str(probs))
    for n, label in (("positive", "Positive"), ("base", "Base"), ("negative", "Negative")):
        pct = round(probs[n] * 100)
        ok = re.search(rf"{label}[^\n]{{0,60}}?\b{pct}\s*%", md) is not None
        add(f"{label} {pct}% 본문 표기", ok)

    for n in ("positive", "base", "negative"):
        s = sc["scenarios"][n]
        lo, hi = f"{s['price_low']:.2f}", f"{s['price_high']:.2f}"
        add(f"{n} 가격 범위 ${lo} ~ ${hi} 본문 표기", f"${lo}" in md and f"${hi}" in md)

    bad = [w for w in FORBIDDEN if w in md]
    add("금지 표현 0건", not bad, f"발견: {bad}" if bad else "")
    n_src = len(re.findall(r"←", md))
    add(f"출처 표기(←) {a.min_sources}회 이상", n_src >= a.min_sources, f"{n_src}회")
    if sc["current_price"] > sc["fair_value_range"]["high"]:
        add("고평가 특례 문구", "모든 시나리오에서 하방 압력" in md)
    add("면책 문구", "투자 권유가 아닌" in md or "투자 결정은 투자자 본인" in md)

    fails = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"] + (f"  [{c['detail']}]" if c["detail"] else ""))
    print(json.dumps({"passed": len(checks) - len(fails), "failed": len(fails)}, ensure_ascii=False))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
