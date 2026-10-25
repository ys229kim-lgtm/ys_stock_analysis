# val_inputs 스키마 (calculate_valuation.py 입력)

```json
{
  "ticker": "KBH", "company": "KB Home", "base_date": "2026-10-25", "currency": "USD",
  "current_price": 47.05,
  "sector_tag": "homebuilder_cyclical",
  "weights": {"pe": 0.4, "pb": 0.4, "pe_norm": 0.2},          // 선택. 없으면 SECTOR_WEIGHTS[sector_tag]
  "weight_rationale": "기본 표 대비 변경 이유",                  // weights 지정 시 필수
  "financials": {
    "eps_for_pe": 3.59, "eps_for_pe_basis": "FY2027E consensus",
    "book_value_per_share": 62.56, "revenue_per_share": null,
    "ebitda": null, "net_debt": 1950.1, "shares_outstanding": 60.76,   // USD m, m
    "fcf": 28.66, "dps_next": 1.0, "payout_ratio": 0.28, "roe": 0.059,
    "eps_normalized": {"low": 4.0, "mid": 4.8, "high": 5.6}
  },
  "assumptions": {
    "pe": {"low": 11, "mid": 13.8, "high": 16},               // 스칼라면 +-15%
    "pb": {"low": 0.65, "mid": 0.80, "high": 0.95},
    "ps": null, "ev_ebitda": null,
    "pe_normalized_multiple": 10,                              // 스칼라 또는 {low,mid,high}
    "ke": 0.10, "wacc": 0.09, "fcf_growth_5y": 0.05, "terminal_growth": 0.025,
    "ddm_growth": 0.03, "rim_roe_long_run": 0.10, "rim_years": 5, "rim_persistence": 0.6,
    "assumption_basis": {"pe": "동종 선행 PER 중앙값 13.8x ...", "pb": "...", "ke": "rf 4.96%(FRED DGS10) + beta x ERP ..."}
  },
  "analyst": {"target_avg": 51.14, "target_median": 49.5, "target_low": 34, "target_high": 70, "count": 17}
}
```

## 단위·규칙
- 금액 USD, `net_debt`·`ebitda`·`fcf`는 **USD millions**, `shares_outstanding`는 millions → 주당 가치 = (밀리언/밀리언).
- `roe`, `payout_ratio`, 할인율·성장률은 소수(0.059 = 5.9%).
- `eps_for_pe`가 음수면 pe 제외. `fcf`≤0이면 dcf 제외. `dps_next`≤0 또는 배당성향≥100%면 ddm 제외.
- `weights`의 키는 `pe, pb, ps, ev_ebitda, pe_norm, dcf, ddm, rim`.
- 계산 가능한 방법이 2종 미만이면 엔진이 오류로 종료한다.
- 결과 파일: 방법별 `{low, mid, high, upside_pct, applied}`, `weighted_avg`, `fair_value_range`, `position`, `weights_effective`, `weights_dropped`, `mid_dispersion_ratio`, `flags`, `consensus_comparison`.
