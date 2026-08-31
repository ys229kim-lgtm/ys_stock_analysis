# 웹·시장 데이터 수집 스킬 (web-data-collector)

## 목적
7대 영역별 웹 검색과 국내/해외 기업 시장 데이터를 수집하여 industry_data JSON을 생성한다.

## 트리거
Step 0 완료 직후 (Step 1과 병렬 시작)

## 수행 절차

### 1. 7대 영역 웹 검색

> **⚙️ 웹 수집 도구 정책 (Firecrawl 우선 / 무료 사용량 초과 시 fallback)**
>
> | 작업 | 1순위 (기본) | Fallback (Firecrawl 사용량 초과 시) |
> |------|-------------|--------------------------------------|
> | 검색 | `mcp__firecrawl-mcp__firecrawl_search` | **`WebSearch`** (내장) |
> | 본문 추출(URL→텍스트) | `mcp__firecrawl-mcp__firecrawl_scrape` | **`mcp__crawl4ai-mcp__scrape`** (단일) / **`mcp__crawl4ai-mcp__scrape_many`** (다수) |
>
> Firecrawl이 사용량/크레딧 오류(HTTP 402·429, 또는 `quota`/`credit`/`insufficient`/`rate limit` 메시지)를
> 반환하면, 재시도하지 말고 이후 모든 호출을 즉시 fallback 도구로 전환한다. crawl4ai는 로컬 브라우저
> 기반이라 사용량 제한이 없다. 본문이 비면(`SCRAPE_FAILED`) 스니펫만 유지한다.

각 영역별 국내+해외 쿼리 실행 (위 도구 정책에 따라 firecrawl_search 또는 WebSearch).

| 영역 | 국내 쿼리 | 해외 쿼리 |
|------|----------|----------|
| 산업 개요·밸류체인 | `{산업명} 산업 구조 밸류체인 2025` | `{industry} value chain structure 2025` |
| 시장 규모·성장률 | `{산업명} 시장 규모 전망 {연도}` | `{industry} market size forecast {year}` |
| 경쟁 구도 | `{산업명} 주요 기업 점유율 순위` | `{industry} market share major players` |
| 수요·공급 사이클 | `{산업명} 수급 재고 현황 {연도}` | `{industry} supply demand cycle inventory` |
| 글로벌 트렌드·기술 | `{산업명} 기술 트렌드 혁신` | `{industry} technology trend innovation` |
| 규제 환경 | `{산업명} 규제 정책 정부 지원` | `{industry} regulation policy subsidy` |
| 단기·중기 전망 | `{산업명} 전망 {연도} {연도+1}` | `{industry} outlook {year} midterm forecast` |

각 쿼리 결과: 상위 5개 URL 스크랩(firecrawl_scrape, 사용량 초과 시 `mcp__crawl4ai-mcp__scrape`) + 스니펫 수집  
페이월 차단 또는 `SCRAPE_FAILED` 시: 스니펫만 저장, `paywall: true` 태그

### 2. 국내 기업 시장 데이터 (korea-stock-mcp)

`mcp__korea-stock-mcp__get_stock_base_info`, `get_stock_trade_info` 호출

대상: 산업 내 주요 국내 기업 상위 5개 (대상 기업 포함)

수집 항목:
- 시가총액, 현재가, 52주 최고·최저
- PER, PBR (get_stock_base_info에서 추출)
- 최근 거래량 추이 (get_stock_trade_info)

### 3. 해외 기업 시장 데이터 (yfinance MCP)

`mcp__yfinance-mcp__get_stock_info` 호출

대상: 산업 내 글로벌 주요 기업 상위 5개

수집 항목:
- marketCap, currentPrice, 52WeekHigh, 52WeekLow
- trailingPE, priceToBook, sector, industry

산업 ETF (해당 시):
- `mcp__yfinance-mcp__get_stock_price_history`로 3개월 추이
- 예: 반도체 → SOXX, SMH / 2차전지 → LIT, BATT

### 4. 성공 기준

- 7대 영역 중 5개 이상 데이터 확보
- 국내 또는 해외 기업 최소 5개 시장 데이터

영역 데이터 부족 시: 해당 섹션에 "데이터 불충분" 태그 후 계속 진행

### 5. 저장 형식

`{출력폴더}/output/industry_data_{날짜}_{기업명}.json`

```json
{
  "collection_date": "2026-06-08",
  "industry": "반도체",
  "web_data": {
    "overview": [...],
    "market_size": [...],
    "competition": [...],
    "supply_demand": [...],
    "global_trends": [...],
    "regulation": [...],
    "outlook": [...]
  },
  "market_data": {
    "domestic": [...],
    "overseas": [...],
    "etf": [...]
  }
}
```

## 스크립트
`scripts/collect_web_data.py` — 웹 검색 + 시장 데이터 수집 자동화

## 참조
`references/search_query_template.md` — 산업별 쿼리 변형 템플릿
