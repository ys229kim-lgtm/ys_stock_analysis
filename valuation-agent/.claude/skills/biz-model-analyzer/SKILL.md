# biz-model-analyzer 스킬

## 목적
Price·Quantity·Cost 3축 프레임워크로 기업의 비즈니스 구조를 정량 분석하고, 경제적 해자(Moat)를 평가한다.

## 분석 프레임워크: P·Q·C

```
수익 = Price × Quantity - Cost

Price (가격 결정력)
  └ 제품/서비스 가격 구조, 가격 결정권, 경쟁 압력, ASP 추이

Quantity (수요량)
  └ 판매량/거래량, 시장점유율, 신규 시장, 고객 이탈/유입

Cost (비용 구조)
  └ COGS 구성, SG&A 효율, 고정비/변동비 레버리지, 규모의 경제
```

## PQC 참조 파일
`.claude/skills/biz-model-analyzer/references/pqc_framework.md`

## 분석 순서

### 1. 데이터 수집 (val_inputs_raw.json + 선행 에이전트 텍스트)

다음 소스에서 사업 구조 관련 텍스트 추출:
- `{financial_path}` 내 사업보고서 섹션 (사업의 개요)
- `{industry_path}` 내 분석 JSON
- `{telegram_path}` 내 리포트 분석 JSON

텍스트 없으면 DART MCP로 직접 수집:
```
mcp__dart-mcp__search_business_information
  corp_code: {8자리 corp_code}
  section: ["사업의 개요", "주요 제품 및 서비스", "매출 현황"]
```

### 2. P·Q·C 축별 분석

각 축별로 아래 항목 작성:

**Price 분석:**
- 핵심 제품/서비스의 가격 수준 및 추이 (수치 + 출처)
- 가격 결정 구조 (시장가격 수용자 vs. 가격 설정자)
- 프리미엄/디스카운트 요인
- ASP (평균판매단가) 방향성

**Quantity 분석:**
- 판매량·출하량 추이 (수치 + 출처)
- 시장점유율 및 변화
- 고객 집중도 (상위 3고객 매출 비중)
- 신규 시장/제품 침투 현황

**Cost 분석:**
- 매출원가율(COGS%) 추이
- 주요 원가 항목 (소재비, 인건비, 에너지비 등)
- 고정비 레버리지 (매출 1% 증가 시 영업이익 변동)
- SG&A/매출 비율 추이

### 3. 비즈니스모델 강약점 도출

**강점 (지속 가능한 경쟁우위):**
- 구체적 수치로 입증 가능한 항목 3~5개

**약점 (구조적 취약점):**
- 수치로 확인된 약점 2~3개

### 4. 경제적 해자(Moat) 평가

아래 5종 해자 각각에 대해 **있음/약함/없음** 판정 + 근거:
- Network Effect (네트워크 효과)
- Switching Cost (전환비용)
- Cost Advantage (비용 우위)
- Intangible Assets (특허·브랜드·규제)
- Efficient Scale (규모 효율)

**Moat 종합 등급:** Wide / Narrow / None

## 출력 형식 (biz_model_{날짜}_{기업명}.json)

```json
{
  "company": "기업명",
  "analysis_date": "YYYY-MM-DD",
  "price_analysis": {
    "key_products": [],
    "pricing_power": "price_setter | price_taker",
    "asp_trend": "상승 | 하락 | 보합",
    "details": "",
    "data_sources": []
  },
  "quantity_analysis": {
    "volume_trend": "성장 | 정체 | 감소",
    "market_share": null,
    "customer_concentration": null,
    "details": "",
    "data_sources": []
  },
  "cost_analysis": {
    "gross_margin_trend": "개선 | 악화 | 보합",
    "cogs_pct": null,
    "sga_pct": null,
    "fixed_cost_leverage": "",
    "details": "",
    "data_sources": []
  },
  "strengths": [],
  "weaknesses": [],
  "moat": {
    "network_effect": "있음 | 약함 | 없음",
    "switching_cost": "있음 | 약함 | 없음",
    "cost_advantage": "있음 | 약함 | 없음",
    "intangible_assets": "있음 | 약함 | 없음",
    "efficient_scale": "있음 | 약함 | 없음",
    "overall_grade": "Wide | Narrow | None",
    "rationale": ""
  }
}
```

## 자기 검증 체크리스트

분석 완료 후 에이전트가 직접 확인:
- [ ] Price·Quantity·Cost 3축 각각 3개 이상 세부 항목 작성
- [ ] 수치가 포함된 항목마다 출처(파일명 또는 MCP 툴명) 기재
- [ ] Moat 5종 모두 판정
- [ ] strengths/weaknesses 합계 5건 이상

검증 실패 항목 발견 시 해당 축 재작성 후 재검증.
