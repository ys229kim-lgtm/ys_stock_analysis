# financial-analysis-agent 산출물 필드 맵

## 개요
financial-agent의 JSON 구조는 기업마다 다를 수 있다.
read_financial_agent.py는 아래 우선순위로 필드를 탐색한다.

## 탐색 경로 우선순위

### 매출액 (revenue_ttm)
1. `summary.revenue`
2. `financials.revenue`
3. `income_statement.revenue`
4. `매출액` (한글 키)

### 영업이익 (operating_income_ttm)
1. `summary.operating_income`
2. `financials.operating_income`
3. `income_statement.operating_income`
4. `영업이익`

### 순이익 (net_income_ttm)
1. `summary.net_income`
2. `financials.net_income`
3. `당기순이익`

### EBITDA
1. `summary.ebitda`
2. `financials.ebitda`
3. 없으면: 영업이익 + 감가상각비로 계산

### 감가상각비 (depreciation)
1. `summary.depreciation`
2. `cash_flow.depreciation`
3. `감가상각비`
4. `depreciation_amortization`

### CapEx
1. `summary.capex`
2. `cash_flow.capex`
3. `설비투자`
4. `capital_expenditure`

### 운전자본 변동 (working_capital_change)
1. `cash_flow.working_capital_change`
2. `운전자본변동`
3. 없으면 0으로 가정

### 순부채 (net_debt)
1. `balance.net_debt`
2. `financials.net_debt`
3. `순차입금`
4. 없으면: 총차입금 - 현금성자산

### 자본총계 (total_equity)
1. `balance.total_equity`
2. `financials.total_equity`
3. `자본총계`

### BPS (book_value_per_share)
1. `per_share.bps`
2. `per_share.book_value`
3. `BPS`
4. `주당순자산`
5. 없으면: 자본총계 / 발행주식수

### EPS TTM (eps_ttm)
1. `per_share.eps_ttm`
2. `per_share.eps`
3. `EPS`
4. `주당순이익`
5. 없으면: 순이익TTM / 발행주식수

### DPS (dps_last)
1. `per_share.dps`
2. `DPS`
3. `주당배당금`

### 주당매출 (revenue_per_share)
1. `per_share.rps`
2. `per_share.revenue`
3. `RPS`
4. 없으면: 매출 / 발행주식수

### 발행주식수 (shares_outstanding)
1. `shares.total_shares`
2. `shares_outstanding`
3. `발행주식수`

### 유효세율 (effective_tax_rate)
1. `income_tax.effective_rate`
2. `tax_rate`
3. `실효세율`
4. 없으면: 22% 가정 (한국 법인세 표준)

---

## industry_tag 탐색 경로

industry-agent의 JSON에서:
1. `industry_tag`
2. `classification.industry_tag`
3. `analysis.industry_tag`
4. `industry_classification.industry_tag`
5. 없으면: null (에이전트가 industry_weight_table.md 보고 선택)

---

## 콘센서스 데이터 탐색 경로 (telegram-agent)

목표주가 목록:
1. `consensus.target_prices`
2. `analysis.target_prices`
3. `output.target_price_list`

평균 EPS 추정:
1. `consensus.avg_eps_estimate`
2. `analysis.avg_eps`

매출 성장률 추정:
1. `consensus.avg_revenue_growth`
2. `analysis.revenue_growth_estimate`
