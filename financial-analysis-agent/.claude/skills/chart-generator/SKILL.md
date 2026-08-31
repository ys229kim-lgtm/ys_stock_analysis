# SKILL: chart-generator

## 목적
financials JSON을 입력받아 12종 PNG 차트를 생성한다.

## 사전 조건
```bash
pip install matplotlib numpy
```
NanumGothic 폰트 권장 (없으면 Malgun Gothic/AppleGothic 자동 폴백).

## 실행 방법

```bash
# 경쟁사 없는 경우
python .claude/skills/chart-generator/scripts/generate_charts.py \
  --input {output_dir}/financials_{date}_{company}.json \
  --output-dir {output_dir}/charts/

# 경쟁사 있는 경우
python .claude/skills/chart-generator/scripts/generate_charts.py \
  --input {output_dir}/financials_{date}_{company}.json \
  --competitors {comp1_financials.json} {comp2_financials.json} \
  --output-dir {output_dir}/charts/
```

## 생성 차트 목록
| 파일명 | 조건 |
|--------|------|
| 01_revenue_profit_trend.png | 항상 |
| 02_margin_trend.png | 항상 |
| 03_roe_roa_trend.png | 항상 |
| 04_debt_stability.png | 항상 |
| 05_cashflow_breakdown.png | 항상 |
| 06_fcf_trend.png | 항상 |
| 07_growth_rate.png | 항상 |
| 08_segment_revenue.png | 세그먼트 데이터 있는 경우만 |
| 09~12 경쟁사 차트 | 경쟁사 있는 경우만 |

## 성공 기준
각 PNG 파일 크기 > 10KB. 스킵된 차트는 로그 기록.
