# data-collector 스킬

## 목적
선행 에이전트 산출물에서 밸류에이션 입력값을 추출하고, 부족한 데이터를 MCP·웹으로 보완한다.

## 데이터 수집 우선순위

```
1순위: financial-analysis-agent 산출물 JSON
2순위: telegram-report-agent 산출물 JSON (콘센서스)
3순위: industry-analysis-agent 산출물 JSON (industry_tag)
4순위: korea-stock-mcp (현재가, 시장 데이터)
5순위: DART MCP (최신 공시 재무)
6순위: 웹 검색 (peer PER/PBR/EV/EBITDA, 베타, 무위험수익률)
```

## 수집 대상 데이터 목록

### 재무 데이터 (financial-agent에서 추출)
| 항목 | JSON 경로 | 단위 |
|------|----------|------|
| 매출액 (최근 4분기) | summary.revenue | 억원 |
| 영업이익 (최근 4분기) | summary.operating_income | 억원 |
| 순이익 (최근 4분기) | summary.net_income | 억원 |
| EBITDA | summary.ebitda (없으면 계산) | 억원 |
| D&A | summary.depreciation | 억원 |
| CapEx | summary.capex | 억원 |
| 운전자본 변동 | summary.working_capital_change | 억원 |
| 순부채 (총차입금-현금) | balance.net_debt | 억원 |
| 자본총계 | balance.total_equity | 억원 |
| 주당순자산 (BPS) | per_share.bps | 원 |
| 주당순이익 (EPS TTM) | per_share.eps_ttm | 원 |
| 주당배당금 (DPS) | per_share.dps | 원 |
| 총발행주식수 | shares.total_shares | 주 |
| 법인세율 | income_tax.effective_rate | % |

### 콘센서스 데이터 (telegram-agent에서 추출)
| 항목 | JSON 경로 |
|------|----------|
| 증권사 목표주가 목록 | consensus.target_prices[] |
| 평균 목표주가 | consensus.avg_target_price |
| 평균 EPS 추정 | consensus.avg_eps_estimate |
| 평균 매출 성장률 추정 | consensus.avg_revenue_growth |

### 시장 데이터 (korea-stock-mcp)
- `mcp__korea-stock-mcp__get_stock_base_info`: 현재가, 시가총액, 52주 고저
- `mcp__korea-stock-mcp__get_stock_trade_info`: PER, PBR, EPS (거래소 제공)

### 거시 데이터 (웹 검색)
| 항목 | 검색 쿼리 예시 |
|------|--------------|
| 한국 국고채 3년 수익률 | "국고채 3년 금리 site:bok.or.kr OR site:kofiabond.or.kr" |
| 코스피 ERP | "KOSPI equity risk premium 2025" |
| 업종 평균 PER/PBR | "{산업명} 업종 평균 PER PBR 2025" |
| 업종 평균 EV/EBITDA | "{산업명} EV EBITDA multiple 2025" |
| 기업 베타 | "{기업명} beta 52주" OR "네이버 금융 {종목코드}" |

## 계산 로직 (데이터 없는 경우)

```python
# EBITDA 없으면:
ebitda = operating_income + depreciation

# NOPAT 없으면:
nopat = operating_income * (1 - effective_tax_rate)

# FCF 없으면:
fcf = nopat + depreciation - capex - working_capital_change

# 순부채 없으면:
net_debt = total_borrowings - cash_and_equivalents

# 주당매출 없으면:
revenue_per_share = revenue / total_shares

# EPS TTM 없으면:
eps_ttm = net_income_ttm / total_shares
```

## 수집 스크립트 실행

```bash
# 1. 선행 에이전트 파일 읽기
uv run read_financial_agent.py \
  --financial-path {financial_path} \
  --telegram-path {telegram_path} \
  --industry-path {industry_path} \
  --output val_inputs_raw.json

# 2. MCP + 웹 보완
uv run collect_data.py \
  --corp-code {종목코드} \
  --company {기업명} \
  --raw-inputs val_inputs_raw.json \
  --output val_inputs_raw.json
```

## 데이터 품질 기준

| 항목 | 최소 요건 |
|------|---------|
| 현재가 | 필수 (없으면 중단 후 사용자 요청) |
| EPS TTM | 필수 (없으면 순이익/주식수 계산) |
| EBITDA | 필수 (없으면 영업이익+D&A 계산) |
| BPS | 필수 (없으면 자본총계/주식수 계산) |
| 무위험수익률 | 필수 (웹 검색으로 반드시 수집) |
| DPS | DDM 미적용으로 처리 (null 허용) |
| 콘센서스 목표가 | 미수집 허용 (콘센서스 섹션 빈 표로 대체) |

## 결과 저장 형식

`val_inputs_raw_{날짜}_{기업명}.json`:
```json
{
  "company": "기업명",
  "ticker": "종목코드",
  "base_date": "YYYY-MM-DD",
  "current_price": null,
  "financials": {
    "revenue_ttm": null,
    "operating_income_ttm": null,
    "net_income_ttm": null,
    "ebitda": null,
    "depreciation": null,
    "capex": null,
    "working_capital_change": null,
    "net_debt": null,
    "total_equity": null,
    "book_value_per_share": null,
    "eps_ttm": null,
    "dps_last": null,
    "revenue_per_share": null,
    "shares_outstanding": null,
    "effective_tax_rate": null
  },
  "consensus": {
    "available": false,
    "target_price_list": [],
    "avg_target_price": null,
    "avg_eps_estimate": null,
    "fcf_growth_from_consensus": null
  },
  "market": {
    "market_cap": null,
    "per_exchange": null,
    "pbr_exchange": null
  },
  "macro": {
    "risk_free_rate": null,
    "market_risk_premium": null,
    "beta": null
  },
  "peer_multiples": {
    "peer_per": null,
    "peer_pbr": null,
    "peer_psr": null,
    "peer_ev_ebitda": null
  },
  "data_sources": {
    "financial_agent_path": null,
    "telegram_agent_path": null,
    "industry_agent_path": null
  },
  "missing_fields": [],
  "notes": []
}
```
