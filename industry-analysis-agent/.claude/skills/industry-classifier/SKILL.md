# 산업 분류 스킬 (industry-classifier)

## 목적
기업명·종목코드를 입력받아 분석 대상 산업을 확정하고 사용자 확인을 완료한다.

## 트리거
워크플로우 최초 시작 시 (Step 0)

## 수행 절차

### 1. yfinance 1차 조회

```python
# scripts/classify_industry.py 실행
python classify_industry.py --company "{기업명}" --code "{종목코드}"
```

반환 필드: `sector`, `industry`, `longName`, `country`

**티커 추론 규칙:**
- 6자리 숫자 코드 → `{코드}.KS` (KOSPI) 또는 `{코드}.KQ` (KOSDAQ) 시도
- 영문명 있으면 yfinance 직접 검색도 병행

### 2. DART 보완 조회 (yfinance 실패·Unknown 시)

`mcp__dart-mcp__search_business_information` 호출:
- 회사명으로 corp_code 조회 후 '사업의 개요' 섹션 추출
- LLM이 텍스트에서 주요 사업 영역과 산업명 추론

### 3. 2단계 레벨 제안

반드시 **넓은 산업**과 **핵심 세그먼트** 두 레벨을 함께 제시:

| 레벨 | 특징 |
|------|------|
| 넓은 산업 | 밸류체인 전체 포함, 글로벌 시장 기준, 시장 규모 크게 잡힘 |
| 핵심 세그먼트 | 기업 매출 핵심 영역, 세밀한 수급 분석 가능, 시장 규모 좁게 잡힘 |

### 4. 복합 사업 판단 기준

다음 중 하나 해당 시 복합 사업으로 판단:
- 사업보고서에 2개 이상 사업 부문 존재
- 단일 사업 매출 비중 < 70%
- yfinance sector와 DART 사업내용이 현저히 다를 때

### 5. 최종 확인 필수

어떤 경우에도 분석 시작 전 사용자에게 확인:
```
'{산업명}' 산업으로 분석을 시작합니다. 맞습니까?
```

## 스크립트
`scripts/classify_industry.py` — yfinance MCP 호출 + DART 보완 로직

## 참조
`references/industry_map.md` — DART 업종코드 → 산업명 매핑 테이블
