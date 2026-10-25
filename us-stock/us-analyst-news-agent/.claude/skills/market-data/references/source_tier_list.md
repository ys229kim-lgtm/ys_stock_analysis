# 소스 신뢰도 등급 (미국)

| Tier | 유형 | 예 | 용도·주의 |
|------|------|----|-----------|
| 1 | 1차 공시·공식 | SEC EDGAR(8-K, 10-Q, 10-K, Form 4, 13D/G), 회사 IR 보도자료, 연준·FRED·BLS·Census, Freddie Mac | 수치의 최종 근거. 충돌 시 우선 |
| 2 | 주요 통신·금융 매체 | Reuters, Bloomberg, WSJ, FT, CNBC, Barron's, Investor's Business Daily | 사건·인용 근거. 유료벽이면 스니펫만 → `confidence: low` |
| 2 | 업종 전문 매체 | HousingWire(주택), Fierce(통신/바이오), Utility Dive 등 | 업종 맥락·경영진 발언 |
| 3 | 데이터 집계 | StockAnalysis, MarketBeat, Yahoo Finance, Public.com, StockStory, TipRanks | 컨센서스·통계의 **교차 확인용**. 집계처마다 값이 다르므로 소스 명시, 최신 변경 미반영 가능 |
| 3 | 실적 콜 요약 | GuruFocus/Yahoo 요약, Seeking Alpha transcript 요약 | 경영진 발언 맥락. 원문 대비 누락 가능 |
| 4 | 블로그·SNS·포럼 | Seeking Alpha 기고, Reddit, X | 근거 불가. 아이디어 탐색용 |

## 규칙
- 핵심 수치(가격, EPS, 가이던스, 목표가)는 가능하면 **Tier 1 또는 2개 이상 독립 소스**.
- 집계 사이트 간 값이 다르면(목표가 평균 $51.14 vs $52.23 vs $56 등) 전부 병기하고 어느 것을 계산에 썼는지 명시.
- 단일 Tier 3 소스에만 있는 사건/수치는 "추정 단계"로 표기.
- 날짜 확인: 기사 게시일과 사건 발생일을 구분. 검색 결과 스니펫에 날짜가 없으면 미확정으로 둔다.
- yfinance MCP rate limit(Too Many Requests) 발생 시: fetch_quote.py → StockAnalysis 순으로 대체.
