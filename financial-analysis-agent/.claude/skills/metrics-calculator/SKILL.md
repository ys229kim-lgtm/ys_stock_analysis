# SKILL: metrics-calculator

## 목적
dart-fetcher가 저장한 정규화 JSON을 입력받아 파생 재무지표를 계산하고 표준화된 financials JSON을 생성한다.

## 실행 방법

```bash
python .claude/skills/metrics-calculator/scripts/calculate_metrics.py \
  --input {dart_normalized_*.json 경로} \
  --output {output_dir}/financials_{date}_{company}.json \
  --company-name {기업명}
```

## 계산 항목
- 영업이익률 = 영업이익 / 매출액 × 100
- 순이익률 = 순이익 / 매출액 × 100
- ROE = 순이익 / 자본총계 × 100
- ROA = 순이익 / 자산총계 × 100
- 부채비율 = 부채총계 / 자본총계 × 100
- 유동비율 = 유동자산 / 유동부채 × 100
- 이자보상배율 = 영업이익 / 이자비용
- FCF = 영업CF - CAPEX
- FCF 마진 = FCF / 매출액 × 100
- YoY 성장률, CAGR(가용 구간 기준 3/5/10년)

## 단위 처리
XBRL decimals 메타데이터 → 조원 자동 변환. 실패 시 억원 가정.

## 성공 기준
- 필수 필드 존재: 매출, 영업이익, 순이익, 자산총계, 부채총계
- ±500% 이상 변동 시 이상치 플래그 (데이터 유지, 리포트 주석)
- 스키마 실패 시 1회 재시도

## 출력
`{output_dir}/financials_{date}_{company}.json`
