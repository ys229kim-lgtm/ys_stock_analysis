# 검색 쿼리 가이드 (firecrawl_search / firecrawl_scrape)

도구 우선순위: `firecrawl_search`(검색) → `firecrawl_scrape`(원문). 검색은 `sources: web`(+`news`), `limit` 5~6. 첫 검색에서 `formats` 없이 URL만 보고, 필요한 페이지만 scrape.
> 스크랩 시 `formats: ["query"]` + `queryOptions`(mode `directQuote`)로 필요한 수치만 추출하면 토큰을 절약한다(단, 표 전체가 필요하면 markdown).

## 컨센서스·통계
- `{company} {TICKER} analyst price target consensus rating {월 연도}`
- 직접 스크랩 URL(가능): `https://stockanalysis.com/stocks/{ticker}/forecast/`, `.../statistics/`, `.../ratings/`
- MarketBeat 인스턴트 알림: `marketbeat {TICKER} price target {월}`
- 실적 추정: stockanalysis forecast 표(FY1/FY2 EPS, 매출) — 일부 연도는 유료(Pro) 가림

## 실적·가이던스
- `{company} {분기} {연도} results press release` (회사 IR 사이트 우선: investor.{domain})
- `{TICKER} Q{n} {연도} earnings call highlights` / `...transcript`
- SEC 원문: 8-K Item 2.02 → fetch_filings.py(밸류에이션 에이전트)의 URL 또는 EDGAR 브라우즈

## 뉴스·리스크
- `{company} lawsuit OR investigation OR recall OR SEC {연도}`
- `{company} acquisition OR divestiture OR CEO OR guidance cut {연도}`
- 업종 쿼리 병행(예: 홈빌더 → `homebuilders mortgage rates new home sales {월 연도}`)
- 영문 기업명 + 티커 병용. 유사명 오염 방지를 위해 `"{정확한 기업명}"` 따옴표.

## 거시 연계
- `Freddie Mac mortgage rates this week`, `FOMC {월 연도} decision`, `10-year Treasury yield {날짜}`
- 거시 수치는 FRED(fetch_fred.py)가 1차 소스. 뉴스는 해석 보완용.

## 주의
- `firecrawl_search` 후 `firecrawl_search_feedback`(id 전달)로 피드백을 남기면 크레딧 환급 — 선택.
- 검색 스니펫만으로 사건을 확정하지 말고, 핵심 사건은 원문을 scrape해서 확인.
- 오래된 전망(예: 연초 NAHB·Fannie Mae)은 현재 금리·정책과 충돌할 수 있으므로 **발행일을 표기**하고 최신 자료와 비교.
