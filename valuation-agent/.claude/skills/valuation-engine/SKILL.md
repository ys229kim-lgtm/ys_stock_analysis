# valuation-engine 스킬

## 목적
DCF, PER/PBR/PSR, EV/EBITDA, DDM(조건부), RIM 5종 밸류에이션을 계산하고 업종별 가중 평균 적정가를 산출한다.

## 참조 파일
- `references/valuation_formulas.md` — 각 방법론의 수식 정의
- `references/wacc_guide.md` — WACC 계산 절차
- `references/industry_weight_table.md` — 업종 태그별 가중치 기준표

## 스크립트 실행 순서

### Step 3: 입력값 준비
```bash
uv run prepare_val_inputs.py \
  --raw-inputs val_inputs_raw_{날짜}_{기업명}.json \
  --output val_inputs_{날짜}_{기업명}.json
```

스크립트 실행 후 에이전트가 직접 `assumptions` 섹션 값 설정:

```json
"assumptions": {
  "risk_free_rate": 0.034,           // 국고채 3년 실시간 조회값
  "market_risk_premium": 0.055,      // KOSPI ERP 추정치
  "beta": 1.2,                       // 52주 베타 또는 업종 베타
  "wacc": null,                      // prepare_val_inputs.py가 계산
  "fcf_growth_rate_5y": 0.08,        // 콘센서스 EPS CAGR or DART FCF CAGR
  "terminal_growth_rate": 0.02,      // 1.5~2.5% 범위
  "peer_per": 18.5,                  // 업종 평균 PER
  "peer_pbr": 2.1,                   // 업종 평균 PBR
  "peer_psr": 1.5,                   // 업종 평균 PSR
  "peer_ev_ebitda": 9.0              // 업종 평균 EV/EBITDA
}
```

가정값 설정 근거를 `weight_rationale` 필드에 기록.

### Step 4: 밸류에이션 계산
```bash
uv run calculate_valuation.py \
  --val-inputs val_inputs_{날짜}_{기업명}.json \
  --output val_results_{날짜}_{기업명}.json
```

## DDM 적용 조건

다음 조건 **모두** 충족 시에만 DDM 적용:
1. DPS > 0 (최근 사업연도 배당 실적 있음)
2. 배당성향 < 100% (지속 가능한 배당)
3. ROE > Ke (성장 가치가 양수)

조건 미충족 시 DDM 결과를 `null`로 설정하고 나머지 4종으로만 계산.

## 가중 평균 산출 방식

`industry_weight_table.md`의 업종 태그별 기준 가중치를 기반으로:

1. 기준 가중치 확인 (예: `성숙주_반도체` → dcf_rim: 0.40, relative: 0.40, ddm: 0.20)
2. DDM 미적용 시 DDM 가중치를 dcf_rim에 50%, relative에 50% 재배분
3. `weight_rationale`에 재배분 이유 기록

**최종 적정가:**
```
적정가 = Σ(각_방법_중간값 × 해당_가중치)
```

**목표가 범위:**
```
하단 = Σ(각_방법_하단값 × 해당_가중치)
상단 = Σ(각_방법_상단값 × 해당_가중치)
```

## 결과 JSON 구조

`val_results_{날짜}_{기업명}.json`:
```json
{
  "company": "기업명",
  "base_date": "YYYY-MM-DD",
  "current_price": 75000,
  "industry_tag": "성숙주_반도체",
  "valuation_weights": {
    "dcf_rim": 0.40,
    "relative": 0.40,
    "ddm": 0.20
  },
  "weight_rationale": "가중치 결정 근거 서술",
  "results": {
    "dcf": {
      "method": "DCF",
      "low": 68000,
      "mid": 82000,
      "high": 96000,
      "upside_pct": 9.3,
      "applied_wacc": 0.089,
      "applied_growth_5y": 0.08,
      "applied_terminal_growth": 0.02
    },
    "per": {
      "method": "PER",
      "low": 70000,
      "mid": 85000,
      "high": 100000,
      "upside_pct": 13.3,
      "applied_peer_per": 18.5,
      "applied_eps": 4595
    },
    "pbr": {
      "method": "PBR",
      "low": 65000,
      "mid": 78000,
      "high": 91000,
      "upside_pct": 4.0,
      "applied_peer_pbr": 2.1,
      "applied_bps": 37143
    },
    "psr": {
      "method": "PSR",
      "low": 60000,
      "mid": 75000,
      "high": 90000,
      "upside_pct": 0.0,
      "applied_peer_psr": 1.5,
      "applied_rps": 50000
    },
    "ev_ebitda": {
      "method": "EV/EBITDA",
      "low": 72000,
      "mid": 88000,
      "high": 104000,
      "upside_pct": 17.3,
      "applied_peer_ev_ebitda": 9.0,
      "applied_ebitda": 320000
    },
    "ddm": null,
    "rim": {
      "method": "RIM",
      "low": 69000,
      "mid": 84000,
      "high": 99000,
      "upside_pct": 12.0,
      "applied_roe": 0.127,
      "applied_ke": 0.092
    }
  },
  "weighted_avg": {
    "low": 68500,
    "mid": 83200,
    "high": 97900,
    "upside_pct": 10.9
  },
  "ddm_applied": false,
  "methods_count": 5,
  "consensus_comparison": {
    "available": true,
    "avg_target_price": 98500,
    "llm_mid": 83200,
    "gap_pct": -15.5,
    "note": "LLM 추정이 콘센서스 대비 15.5% 낮음"
  }
}
```
