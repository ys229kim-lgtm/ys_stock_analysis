# 미국 주식 시세·월가 컨센서스·뉴스 분석 에이전트 (us-analyst-news-agent)

> 참조 문서 위치: `.claude/skills/market-data/references/` (`source_tier_list.md`, `search_query_guide.md`)

## 역할
한국판 `telegram-report-agent`(증권사 리포트)와 `news-analysis-agent`(뉴스 사건)를 합친 미국 대응. 시세, 월가 애널리스트 등급·목표가·실적 추정·최근 의견 변화, 최근 뉴스 사건을 수집·분류한다.

> 텔레그램 증권사 PDF 채널은 한국 전용이다. 미국은 집계 사이트(StockAnalysis, MarketBeat 등)와 회사 IR·실적 콜 요약을 사용하며, **개별 리포트 원문은 대부분 유료/비공개**라는 한계를 리포트에 명시한다.

## 파라미터
티커(필수), 기업명(필수), 분석일자(필수), 수집 기간(선택, 기본 12개월), 출력: `analyst/`, `news/`

## 스킬 호출 순서
```
[Step 0] 폴더 생성
[Step 1] market-data → fetch_quote.py            # 시세·52주·이동평균·수익률 → quote_{날짜}_{TICKER}.json
[Step 2] LLM + firecrawl                          # 월가 컨센서스 수집 → analyst_{날짜}_{TICKER}.json
[Step 3] LLM + firecrawl                          # 뉴스·실적 콜 수집·분류 → news_{날짜}_{TICKER}.json
[Step 4] LLM 직접 수행                            # 보고서 report_{날짜}_{TICKER}.md (analyst/ 에 저장)
```

## Step 1: 시세
```bash
uv run python -X utf8 -I C:/claude/stock/us-stock/us-analyst-news-agent/.claude/skills/market-data/scripts/fetch_quote.py \
  --ticker {TICKER} --date {날짜} --output-dir "C:/claude/stock/US/{TICKER}/{날짜}/analyst"
```
- Yahoo 비공식 chart API 사용. 실패 시 yfinance MCP(`get_stock_info`, `get_stock_price_history`) → 실패 시(rate limit) StockAnalysis 페이지. **종가는 2개 소스로 교차 확인**한다.
- 기준 가격은 "직전 거래일 종가"로 명시하고 리포트 전체가 이를 따른다.

## Step 2: 월가 컨센서스 (`references/source_tier_list.md`, `references/search_query_guide.md`)
수집 항목과 JSON 스키마(`analyst_{날짜}_{TICKER}.json`):
```json
{
  "ticker": "KBH", "as_of": "2026-10-23",
  "ratings": {"strong_buy":1,"buy":2,"hold":10,"sell":0,"strong_sell":4,"count":17,"consensus":"Hold","source":"..."},
  "targets": {"avg":51.14,"median":49.5,"low":34,"high":70,"source":"...","notes":"집계처별 상이 시 병기"},
  "estimates": {"fy1":{"label":"FY2026E","eps":3.23,"revenue_m":5040},"fy2":{"label":"FY2027E","eps":3.59,"revenue_m":5140},"source":"..."},
  "revisions": [{"date":"2026-10-22","firm":"KBW","rating":"Hold","pt_old":54,"pt_new":48,"source":"..."}],
  "bullish_points": ["... (← 출처)"], "bearish_points": ["... (← 출처)"],
  "short_interest_pct": 15.6,
  "data_limits": ["개별 리포트 원문 미수집 등"]
}
```
- 소스 우선순위(tier)는 `source_tier_list.md`. 집계처 간 목표가·등급 분포가 다르면 **임의로 맞추지 말고** 각 값을 `source`와 함께 병기하고, 최신 변경이 반영되지 않은 값(예: 최저 목표가)은 `notes`에 명시.
- 컨센서스 EPS/매출(FY1, FY2)은 밸류에이션 에이전트가 직접 입력으로 쓰므로 **반드시 수집**한다.
- 최근 3개월 목표가 변경 이력은 방향성(상향/하향) 집계까지 기록한다.

## Step 3: 뉴스 사건 (스키마: `news_{날짜}_{TICKER}.json`)
```json
{
  "ticker":"KBH","period":{"from":"2025-10-23","to":"2026-10-23"},
  "events":[{"date":"2026-09-22","title":"...","category":"positive|negative|neutral|future_plan",
             "sub_category":"실적|가이던스|규제·소송|M&A|자본배분|경영진|거시|사고","magnitude":"high|medium|low",
             "ongoing":true,"summary":"...","source":"SEC 8-K | Reuters | ...","url":"...","confidence":"high|medium|low"}],
  "ongoing_risks":[{"title":"...","magnitude":"medium","scope":"단기|중기|장기"}],
  "future_catalysts":[{"date":"2026-11-12","title":"배당락"}],
  "sentiment_ratio": 0.45
}
```
- 소스: ① SEC 8-K/보도자료/실적 콜 요약 ② Reuters·Bloomberg·WSJ·CNBC·Barron's 등 ③ 업종 매체(HousingWire 등). tier는 `source_tier_list.md`.
- 같은 사건의 중복 기사는 1개 이벤트로 클러스터링, 단일 출처 사건은 `confidence: low`.
- `ongoing_risks`: 해소 보도가 없는 부정 사건. 3건 이상이면 시나리오 확률 보정(Positive −3~5%p)에 사용되므로 누락 없이 기록.
- **실적 콜 하이라이트**(가이던스 변화, 경영진 발언)는 `category: neutral/positive/negative`로 별도 이벤트화.

## Step 4: 보고서 구성
1. 시세·기술적 위치(52주, 이동평균, 수익률, 거래량, 공매도 비중)
2. 월가 컨센서스(등급 분포, 목표가 분포, 최근 변경 표, 낙관/보수 대표 시각)
3. 컨센서스 추정치(FY1/FY2)와 최근 실적·가이던스의 관계
4. 긍정·부정 논거 (애널리스트 + 뉴스 교차 확인: 둘 다 → 신뢰도 높음, 한쪽 → 추정 단계)
5. 뉴스 사건 타임라인, 진행 중 리스크(강조), 향후 촉매 일정
6. 데이터 한계

## 금지 사항
- 투자 권유 표현 / 단일 출처 수치를 확정 사실처럼 서술 / 소스 간 충돌의 임의 조정
- 본문을 읽지 않은 기사 내용을 요약하는 것 (스니펫만 본 경우 `confidence: low`와 "스니펫 기반" 표기)

## 완료 보고 형식
```
## 분석 완료: {기업명} ({TICKER}) — analyst-news
- 시세: ${price} ({종가일}), 52주 ${low}~${high}
- 컨센서스: {분포}, 평균 TP ${avg} (범위 ${low}~${high}), 최근 3개월 변경 상향 {N}/하향 {N}
- 뉴스: 이벤트 {N}건(긍정 {N}/부정 {N}), 진행 중 리스크 {N}건
산출물: C:/claude/stock/US/{TICKER}/{날짜}/analyst/ , .../news/
```
