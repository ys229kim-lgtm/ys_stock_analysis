# disclosure-monitor 스킬

## 목적
최근 6개월 수시공시를 수집하여 밸류에이션에 영향을 주는 이벤트를 중요도별로 분류하고, 리스크·기회 요인을 식별한다.

## 수집 방법

### DART MCP 활용
```
mcp__dart-mcp__search_disclosure
  corp_code: {8자리 corp_code}
  bgn_de: {6개월 전 YYYYMMDD}
  end_de: {오늘 YYYYMMDD}
  pblntf_ty: "B"  // 수시공시
```

### korea-stock-mcp 보완
```
mcp__korea-stock-mcp__get_disclosure_list
  corp_code: {종목코드}
  count: 50
```

## 중요도 분류 기준

### HIGH (즉시 밸류에이션 영향)
- 대규모 유상증자 / 주식발행 (주가 희석)
- 대규모 자사주 매입 / 소각 (EPS 개선)
- 주요 사업 양수·양도 (자산가치 변동)
- 대규모 계약 체결 (매출 가시성 급변)
- 경영진 교체 (전략 방향 불확실성)
- 최대주주 변경
- 영업정지·제재·소송 (리스크 현실화)
- 실적 서프라이즈/쇼크 (영업이익 ±20% 이상)

### MEDIUM (중기 밸류에이션 영향)
- 신규 생산설비·공장 투자 (CapEx 증가, 미래 Quantity 증가)
- 사업부 분할·합병
- 배당 정책 변경 (DDM 가정 변경)
- 신제품 출시·연구개발 성과
- 주요 파트너십 체결

### LOW (모니터링 수준)
- 임원 주식 취득·처분
- 정기 공시 일정 (분기보고서 예정)
- 사소한 인사 변동

## 공시 이벤트 분석 원칙

1. **원문 수치만 기재** — 공시 본문에 없는 수치 추론 금지
2. **밸류에이션 연계** — 각 HIGH 이벤트마다 "주당 적정가에 미치는 영향 방향" 기술 (긍정/부정/중립)
3. **진행 중 이슈** — 완결되지 않은 이벤트 별도 섹션으로 관리
4. **향후 예정 일정** — 공시에서 확인된 예정일 (결산 발표, 주주총회 등)

## 출력 형식 (disclosures_{날짜}_{기업명}.json)

```json
{
  "company": "기업명",
  "collection_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "total_count": 15,
  "high_count": 2,
  "medium_count": 5,
  "low_count": 8,
  "events": [
    {
      "date": "YYYY-MM-DD",
      "title": "공시 제목",
      "importance": "high | medium | low",
      "category": "유상증자 | 자사주 | 계약 | 경영진 | 실적 | 기타",
      "summary": "공시 내용 요약 (원문 수치 포함)",
      "valuation_impact": "positive | negative | neutral",
      "impact_note": "밸류에이션에 미치는 영향 방향 서술",
      "status": "완료 | 진행중 | 예정"
    }
  ],
  "ongoing_issues": [
    {
      "title": "진행 중 이슈 제목",
      "start_date": "YYYY-MM-DD",
      "current_status": "상황 설명",
      "next_milestone": "다음 분기 결산 발표 (예정: 2026-08-14)"
    }
  ],
  "upcoming_schedule": [
    {
      "date": "YYYY-MM-DD",
      "event": "이벤트명"
    }
  ],
  "summary_note": "공시 전체 요약: 밸류에이션 관점에서 주목할 사항"
}
```

## 자기 검증 체크리스트

- [ ] 최근 6개월 공시 전수 확인 (0건이면 "공시 없음" 명시)
- [ ] HIGH 이벤트 전부 valuation_impact 기재
- [ ] ongoing_issues 섹션 존재 (없으면 빈 배열)
- [ ] upcoming_schedule 섹션 존재 (없으면 빈 배열)
- [ ] summary_note 작성 완료
