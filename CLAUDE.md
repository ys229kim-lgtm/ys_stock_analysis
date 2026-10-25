# 기업 종합 분석 오케스트레이터

## 역할
"특정기업분석을 해줘" 명령 수신 시 `financial-analysis-agent`, `telegram-report-agent`, `news-analysis-agent`, `industry-analysis-agent` 4개를 **동시에** 실행하고, 완료 후 `valuation-agent`를 **순차 실행**하며, 마지막으로 `final-report-agent`를 **순차 실행**하여 DART 재무분석, 텔레그램 증권사 리포트 분석, 뉴스 사건 분석, 산업 구조·전망 분석, 비즈니스모델·밸류에이션·공시 분석, **5개 에이전트 산출물 통합 최종 리포트 생성**을 수행한다.

---

## 트리거 명령
다음 표현 수신 시 즉시 병렬 실행:
- "특정기업분석을 해줘"
- "기업분석 해줘"
- "종합분석 해줘"
- "○○ 분석해줘" (기업명 포함 분석 요청)

> **미국 상장 종목(NYSE/NASDAQ)은 이 파이프라인이 아니라 `C:/claude/stock/us-stock/CLAUDE.md`(미국 주식 오케스트레이터)를 따른다.** 예: "미국주식 KBH 분석해줘", "엔비디아 분석해줘". DART·텔레그램 기반인 이 문서의 에이전트는 한국(KOSPI/KOSDAQ) 종목 전용이다.

---

## 파라미터 파싱 (실행 전 필수)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| 기업명 | 필수 | 한글 기업명 (예: 삼성전자) |
| 종목코드 | 선택 | 6자리 DART 종목코드 (예: 005930) |
| 경쟁사코드 | 선택 | financial-analysis-agent 전용, 쉼표 구분 |
| 수집 기간 | 선택 | telegram-report-agent 전용, 미입력 시 최근 1년 |

| 영문 기업명 | 선택 | news-analysis-agent 전용, 해외 뉴스 수집 강화 |
| 산업명 | 선택 | industry-analysis-agent 전용, 미입력 시 에이전트가 자동 분류 후 사용자 확인 |

**기업명이 없으면 여섯 에이전트 실행 전 반드시 사용자에게 먼저 요청한다.**

---

## 병렬 실행 방법

명령과 파라미터 확인 후, **단일 응답에서 Agent 도구 4개(Agent 1~4)를 동시에 호출**한다. Agent 5(valuation-agent)는 1~4 완료 후 별도로 실행한다. Agent 6(final-report-agent)은 1~5 완료 후 별도로 실행한다.

### Agent 1: financial-analysis-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/financial-analysis-agent
  CLAUDE.md(C:/claude/stock/financial-analysis-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 재무실적 분석을 수행하라.
  - 종목코드: {종목코드}
  - 기업명: {기업명}
  - 경쟁사코드: {경쟁사코드 또는 없음}
  - 분석기준연도: {연도 또는 미입력}
```

### Agent 2: telegram-report-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/telegram-report-agent
  CLAUDE.md(C:/claude/stock/telegram-report-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 증권사 리포트 수집·분석을 수행하라.
  - 기업명: {기업명}
  - 종목코드: {종목코드 또는 없음}
  - 수집 기간: {기간 또는 미입력(최근 1년 자동 적용)}
```

### Agent 3: news-analysis-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/news-analysis-agent
  CLAUDE.md(C:/claude/stock/news-analysis-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 뉴스 수집·사건 분석을 수행하라.
  - 기업명: {기업명}
  - 영문 기업명: {영문 기업명 또는 없음}
  - 종목코드: {종목코드 또는 없음}
  - 수집 기간: {기간 또는 미입력(최근 2년 자동 적용)}
```

### Agent 4: industry-analysis-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/industry-analysis-agent
  CLAUDE.md(C:/claude/stock/industry-analysis-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 산업 구조·전망 분석을 수행하라.
  - 기업명: {기업명}
  - 영문 기업명: {영문 기업명 또는 없음}
  - 종목코드: {종목코드 또는 없음}
  - 산업명: {산업명 또는 미입력(에이전트가 자동 분류 후 사용자 확인)}
```

### Agent 5: valuation-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/valuation-agent
  CLAUDE.md(C:/claude/stock/valuation-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 비즈니스모델·밸류에이션·공시 분석을 수행하라.
  - 기업명: {기업명}
  - 종목코드: {종목코드}
  - base_path: C:/claude/stock/{기업명}/{날짜}/
  - financial_agent_path: C:/claude/stock/{기업명}/{날짜}/financial/
  - telegram_agent_path: C:/claude/stock/{기업명}/{날짜}/telegram/
  - industry_agent_path: C:/claude/stock/{기업명}/{날짜}/industry/
```

**Agent 5 실행 시점:** Agent 1~4 완료 후 실행. 앞선 에이전트의 산출물을 입력으로 사용하기 때문.

### Agent 6: final-report-agent
```
subagent_type: claude
run_in_background: false
prompt:
  작업 디렉토리: C:/claude/stock/final-report-agent
  CLAUDE.md(C:/claude/stock/final-report-agent/CLAUDE.md)의 지침에 따라
  아래 파라미터로 최종 종합 리포트를 생성하라.
  - 기업명: {기업명}
  - 날짜: {날짜}
  - financial_path: C:/claude/stock/{기업명}/{날짜}/financial/
  - telegram_path: C:/claude/stock/{기업명}/{날짜}/telegram/
  - news_path: C:/claude/stock/{기업명}/{날짜}/news/
  - industry_path: C:/claude/stock/{기업명}/{날짜}/industry/
  - valuation_path: C:/claude/stock/{기업명}/{날짜}/valuation/
  - output_path: C:/claude/stock/{기업명}/{날짜}/final/
```

**Agent 6 실행 시점:** Agent 1~5 완료 후 실행. 5개 에이전트 전체 산출물을 입력으로 사용하기 때문.
**Agent 6 실패 에이전트 처리 정책:**
- 필수 에이전트(DART·Valuation) 실패 시 → 사용자에게 확인 후 실행
- 선택 에이전트(Telegram·News·Industry) 실패 시 → 사용자에게 알린 후 자동 진행

---

## 실행 규칙

- **Agent 1~4 병렬 실행, Agent 5는 1~4 완료 후 순차 실행, Agent 6은 1~5 완료 후 순차 실행.**
- **여섯 에이전트 각각 독립 실행** — 한쪽 실패가 다른 쪽에 영향을 주지 않는다.
- **출력 폴더 — 기업명/날짜 아래 에이전트별 서브폴더로 통합 관리:**
  - financial-analysis-agent → `C:/claude/stock/{기업명}/{날짜}/financial/`
  - telegram-report-agent → `C:/claude/stock/{기업명}/{날짜}/telegram/`
  - news-analysis-agent → `C:/claude/stock/{기업명}/{날짜}/news/`
  - industry-analysis-agent → `C:/claude/stock/{기업명}/{날짜}/industry/`
  - valuation-agent → `C:/claude/stock/{기업명}/{날짜}/valuation/`
  - final-report-agent → `C:/claude/stock/{기업명}/{날짜}/final/`
- industry-analysis-agent는 Step 0(산업 분류 확인)에서 사용자 응답을 요구한다 — 다른 세 에이전트와 동시에 실행하되, 사용자가 산업 분류 확인 질문에 답하면 에이전트가 이어서 분석을 진행한다.
- 여섯 에이전트 모두 완료되면 각 산출물 경로를 취합하여 사용자에게 요약 보고한다.

---

## 완료 보고 형식

```
## 기업 종합 분석 완료: {기업명}

### DART 재무분석 (financial-analysis-agent)
- 상태: 완료 / 실패
- 산출물: `C:/claude/stock/{기업명}/{날짜}/financial/`

### 증권사 리포트 분석 (telegram-report-agent)
- 상태: 완료 / 실패
- 산출물: `C:/claude/stock/{기업명}/{날짜}/telegram/`

### 뉴스 사건 분석 (news-analysis-agent)
- 상태: 완료 / 실패
- 수집 기사: N건 | 유효 클러스터: N개 | 진행 중 리스크: N건
- 산출물: `C:/claude/stock/{기업명}/{날짜}/news/`

### 산업 구조·전망 분석 (industry-analysis-agent)
- 상태: 완료 / 실패
- 분석 산업: {산업명} | 텔레그램 리포트: N건 | 웹 수집: N건
- 산출물: `C:/claude/stock/{기업명}/{날짜}/industry/`

### 밸류에이션 분석 (valuation-agent)
- 상태: 완료 / 실패
- 업종 태그: {industry_tag} | 적용 방법: N종 | DDM: 적용/미적용
- 가중 평균 적정가: {N}원 ({upside_pct}% upside/downside)
- 산출물: `C:/claude/stock/{기업명}/{날짜}/valuation/`

### 최종 종합 리포트 (final-report-agent)
- 상태: 완료 / 실패
- 사용 에이전트: N개 / 6개 | 누락: {누락 목록 또는 없음}
- 가중 평균 적정가: {N}원 | Upside: {upside_pct}%
- 시나리오: Positive {X}% / Base {Y}% / Negative {Z}%
- 산출물: `C:/claude/stock/{기업명}/{날짜}/final/`
  - `integrated_{날짜}_{기업명}.json`
  - `report_{날짜}_{기업명}.md`
  - `report_{날짜}_{기업명}.docx`
```

---

## 하위 에이전트 디렉토리 구조

```
C:/claude/stock/
├── CLAUDE.md                           ← 이 파일 (오케스트레이터)
├── financial-analysis-agent/
│   └── CLAUDE.md                       ← DART 재무분석 에이전트 지침
├── telegram-report-agent/
│   └── CLAUDE.md                       ← 텔레그램 리포트 분석 에이전트 지침
├── news-analysis-agent/
│   ├── CLAUDE.md                       ← 뉴스 수집·사건 분석 에이전트 지침
│   ├── scripts/
│   └── references/
├── industry-analysis-agent/
│   ├── CLAUDE.md                       ← 산업 구조·전망 분석 에이전트 지침
│   ├── .claude/skills/
│   └── docs/
├── valuation-agent/
│   ├── CLAUDE.md                       ← 밸류에이션 분석 에이전트 지침
│   ├── .claude/skills/                 ← 스킬 파일
│   └── docs/
├── final-report-agent/
│   ├── CLAUDE.md                       ← 최종 종합 리포트 에이전트 지침
│   └── .claude/skills/
│       ├── input-validator/            ← 입력 검증·정규화 스킬
│       ├── signal-analyzer/            ← 신호 정합성 분석 스킬 (LLM 참조용)
│       ├── report-synthesizer/         ← 섹션 작성·시나리오·자기 검증 스킬 (LLM 참조용)
│       └── report-builder/             ← JSON·md·docx 생성 스킬
└── {기업명}/                           ← 실행 시 생성되는 기업별 통합 산출물 폴더
    └── {YYYYMMDD}/                     ← 날짜별 분석 결과
        ├── financial/                  ← financial-analysis-agent 산출물
        ├── telegram/                   ← telegram-report-agent 산출물
        ├── news/                       ← news-analysis-agent 산출물
        ├── industry/                   ← industry-analysis-agent 산출물
        ├── valuation/                  ← valuation-agent 산출물
        └── final/                      ← final-report-agent 산출물
```
