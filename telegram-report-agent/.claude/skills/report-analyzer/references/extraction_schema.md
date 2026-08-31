# 리포트별 추출 항목 스키마 (Step 4)

## JSON 구조

```json
{
  "source_file": "파일명 (확장자 포함)",
  "channel": "수신 채널명",
  "report_date": "YYYY-MM-DD (리포트 발행일, 불명확 시 파일명에서 추출)",
  "securities_firm": "증권사명 (추출 불가 시 null)",
  "analyst": "애널리스트명 (추출 불가 시 null)",
  "investment_opinion": "Buy | Hold | Sell | 명시없음",
  "target_price": 90000,
  "current_price_at_report": 75000,
  "bullish_points": ["포인트1", "포인트2"],
  "bearish_points": ["포인트1", "포인트2"],
  "risk_factors": ["리스크1", "리스크2"],
  "earnings_estimates": {
    "revenue": {"value": 320, "unit": "조원", "period": "2026"},
    "operating_profit": {"value": 45, "unit": "조원", "period": "2026"},
    "eps": {"value": 8500, "period": "2026"}
  },
  "key_catalysts": ["촉매1", "촉매2"],
  "quality_flag": "normal | low_quality | ocr_only",
  "confidence": "high | medium | low",
  "irrelevant": false,
  "parse_failed": false
}
```

---

## 필드별 추출 지침

### investment_opinion
- `"Buy"`: 매수, 강력매수, Overweight, Outperform, Strong Buy 등
- `"Hold"`: 중립, 보유, Neutral, Market Perform, Hold 등
- `"Sell"`: 매도, Underperform, Sell, Underweight 등
- `"명시없음"`: 투자의견이 리포트에 명시되지 않은 경우 (임의 판단 금지)

### target_price / current_price_at_report
- 원문에 명시된 숫자만 추출 (단위: 원)
- "목표주가 90,000원" → `90000`
- 명시 없으면 `null`
- **추론·계산 절대 금지**

### bullish_points / bearish_points
- 리포트에서 **긍정적 근거**와 **부정적 근거/우려**를 각각 추출
- 원문을 요약하되 의미 왜곡 없이 간결하게 기술
- 최소 1개, 최대 10개 항목

### risk_factors
- 단기/중장기 리스크, 불확실성 요인
- `bearish_points`와 중복될 수 있으나 별도 추출

### earnings_estimates
- `revenue`, `operating_profit`, `eps` 각각 독립 추출
- 명시 없는 항목은 전체 필드를 `null`로 설정
- 단위는 원문 그대로 기재 (`억원`, `조원`, `백만원` 등)
- period: 추정 기준 연도 (예: `"2026"`)

### quality_flag
- `collection_meta` JSON의 해당 파일 `quality_flag` 값을 그대로 사용
- 에이전트가 자체 판단으로 변경 가능 (텍스트가 명백히 저품질일 때)

### confidence
- `"high"`: 텍스트 품질 양호, 핵심 항목 대부분 추출 성공
- `"medium"`: 일부 항목 null, 텍스트 품질 보통
- `"low"`: `low_quality` 또는 `ocr_only` 플래그이거나 핵심 항목 대부분 null

### irrelevant
- 리포트 텍스트가 검색 기업과 **명백히 무관**하면 `true`
- 기업명이 한 번도 언급되지 않거나 타 기업 단독 리포트이면 `true`
- 불확실하면 `false` 유지 (과도한 필터링 금지)

---

## 판단 원칙

1. **원문에 명시된 수치만 추출** — 추론·계산·보간 금지
2. **투자의견 명시 없으면 `"명시없음"`** — 문맥 추론으로 임의 부여 금지
3. **`low_quality` 파일은 항목 일부 null 허용** — 억지 추출 시도 금지
4. **수치 필드 타입**: 숫자 또는 `null`만 허용, 문자열("N/A", "미기재" 등) 혼입 금지

---

## 자기 검증 체크리스트

추출 완료 후 아래 항목을 점검하고, 실패 시 해당 리포트 재분석 1회:

- [ ] `source_file` 존재 및 비어있지 않음
- [ ] `report_date` 존재 (파일명에서 날짜 추출 시도 후 불명확하면 `"unknown"`)
- [ ] `bullish_points` 배열 존재 (빈 배열 허용)
- [ ] `bearish_points` 배열 존재 (빈 배열 허용)
- [ ] `investment_opinion` 존재 (null 불허)
- [ ] 수치 필드(`target_price`, `current_price_at_report`, `earnings_estimates` 내 `value`)가 숫자 또는 null
