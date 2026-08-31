"""
MCP 및 웹 검색으로 val_inputs_raw.json의 누락 데이터를 보완.
이 스크립트는 에이전트가 직접 MCP 도구를 호출하는 방법을 안내한다.
실제 MCP 호출은 에이전트가 수행하며, 이 스크립트는 보완 결과를 val_inputs_raw.json에 병합한다.
"""

import argparse
import json
from pathlib import Path
from datetime import date


SUPPLEMENT_GUIDE = """
## 누락 데이터 보완 가이드 (에이전트 실행 지침)

이 스크립트 실행 전, 에이전트가 다음 MCP 도구를 호출하여 데이터를 수집해야 한다.

### 1. 현재가 + 시장 데이터
```
mcp__korea-stock-mcp__get_stock_base_info
  종목코드: {ticker}
→ 반환: 현재가(current_price), 시가총액(market_cap), 52주고/저
```

```
mcp__korea-stock-mcp__get_stock_trade_info
  종목코드: {ticker}
→ 반환: PER, PBR, EPS (거래소 공식 수치)
```

### 2. 무위험수익률 (국고채 3년)
```
firecrawl_search: "국고채 3년 수익률 site:bok.or.kr OR site:kofiabond.or.kr"
OR: "한국 기준금리 국고채 3년 2025"
→ risk_free_rate (소수점: 예 0.034)
```

### 3. ERP (시장위험프리미엄)
```
firecrawl_search: "KOSPI equity risk premium 2025 ERP"
→ market_risk_premium (기본값 0.055 적용)
```

### 4. 베타
```
firecrawl_search: "{ticker} 베타 beta 52주"
OR: 네이버 금융 "{기업명}" 종목 분석 페이지
→ beta (없으면 업종 평균 베타 사용)
```

### 5. 업종 평균 Peer 배수
```
firecrawl_search: "{산업명} 업종 평균 PER PBR 2025 한국 KOSPI"
firecrawl_search: "{산업명} EV EBITDA multiple sector 2025"
→ peer_per, peer_pbr, peer_ev_ebitda
```

### 6. EPS / BPS / 주식수 (재무에이전트에 없는 경우)
```
mcp__dart-mcp__search_disclosure
  corp_code: {corp_code}
  pblntf_ty: "A" (정기공시)
→ EPS, BPS, DPS 등 직접 추출
```
"""


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_supplement(raw: dict, supplement: dict) -> dict:
    """에이전트가 수집한 보완 데이터를 raw에 병합."""
    # current_price
    if raw.get("current_price") is None and supplement.get("current_price"):
        raw["current_price"] = supplement["current_price"]
        raw["notes"].append("current_price: korea-stock-mcp 수집")

    # market
    for k in ("market_cap", "per_exchange", "pbr_exchange"):
        if raw["market"].get(k) is None and supplement.get("market", {}).get(k):
            raw["market"][k] = supplement["market"][k]

    # macro
    for k in ("risk_free_rate", "market_risk_premium", "beta"):
        if raw["macro"].get(k) is None and supplement.get("macro", {}).get(k):
            raw["macro"][k] = supplement["macro"][k]

    # peer_multiples
    for k in ("peer_per", "peer_pbr", "peer_psr", "peer_ev_ebitda"):
        if raw["peer_multiples"].get(k) is None and supplement.get("peer_multiples", {}).get(k):
            raw["peer_multiples"][k] = supplement["peer_multiples"][k]

    # financials 개별 보완
    for k, v in supplement.get("financials", {}).items():
        if raw["financials"].get(k) is None and v is not None:
            raw["financials"][k] = v

    # missing_fields 업데이트
    raw["missing_fields"] = [
        k for k, v in raw["financials"].items()
        if v is None and k not in ("depreciation", "capex", "working_capital_change", "dps_last", "revenue_per_share")
    ]

    # 필수 macro 누락 기본값 적용
    if raw["macro"]["market_risk_premium"] is None:
        raw["macro"]["market_risk_premium"] = 0.055
        raw["notes"].append("market_risk_premium: 기본값 0.055 적용 (KOSPI 역사적 ERP)")

    return raw


def print_supplement_guide(ticker: str, company: str):
    guide = SUPPLEMENT_GUIDE.replace("{ticker}", ticker).replace("{기업명}", company)
    print(guide)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corp-code", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--raw-inputs", required=True)
    parser.add_argument("--supplement-json", default="",
                        help="에이전트가 수집한 보완 데이터 JSON (선택)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    raw = load_json(args.raw_inputs)

    if args.supplement_json and Path(args.supplement_json).exists():
        supplement = load_json(args.supplement_json)
        raw = merge_supplement(raw, supplement)
        print(f"[OK] 보완 데이터 병합 완료")
    else:
        # 보완 데이터가 없으면 가이드 출력
        print_supplement_guide(
            ticker=args.corp_code or raw.get("ticker", ""),
            company=args.company or raw.get("company", ""),
        )
        print("\n[INFO] 위 가이드에 따라 MCP로 데이터 수집 후 --supplement-json 옵션으로 재실행하거나,")
        print("[INFO] 에이전트가 직접 raw JSON을 업데이트하세요.")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"[OK] 저장: {out_path}")

    missing = raw.get("missing_fields", [])
    if missing:
        print(f"[WARN] 여전히 누락된 핵심 필드: {missing}")
    else:
        print("[OK] 모든 필수 필드 수집 완료")


if __name__ == "__main__":
    main()
