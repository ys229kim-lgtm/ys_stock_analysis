# 미국 주식 종합 분석 오케스트레이터

## 역할
"미국 주식 분석" 명령 수신 시 `us-financial-agent`, `us-analyst-news-agent`, `us-industry-macro-agent` 3개를 **동시에** 실행하고, 완료 후 `us-valuation-agent`를 **순차 실행**, 마지막으로 `us-final-report-agent`를 **순차 실행**한다.
SEC 재무·월가 컨센서스·뉴스·산업/거시·밸류에이션·SEC 공시 분석을 **하나의 최종 종합 리포트(USD)** 로 통합한다.

> 한국 종목(KOSPI/KOSDAQ)은 이 파이프라인이 아니라 `C:/claude/stock/CLAUDE.md`(DART·텔레그램 기반) 오케스트레이터를 사용한다.

---

## 트리거 명령
- "미국주식 분석해줘 {티커 또는 영문 기업명}"
- "{티커/영문 기업명} 미국 주식 분석", "US stock analysis {ticker}"
- 티커가 NYSE/NASDAQ 종목이고 한국 종목이 아닌 분석 요청 (예: "KBH 분석해줘", "엔비디아 분석해줘")

---

## 파라미터 파싱 (실행 전 필수)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| 티커 | 필수 | 예: KBH. 기업명만 오면 SEC 티커 목록으로 확인 후 사용자에게 1회 확인 |
| 기업명 | 자동 | SEC `entityName`으로 보완 (영문 정식명). 폴더·파일명에는 티커 사용 |
| 분석일자 | 자동 | 오늘 날짜 YYYYMMDD. **시세 기준일은 직전 거래일 종가**로 명시 |
| 업종 태그 | 선택 | 미입력 시 industry agent가 SIC/GICS로 분류 (`us-industry-macro-agent/.../sector_tag_map.md`) |
| 경쟁사 티커 | 선택 | 쉼표 구분. 미입력 시 industry agent가 4~5개 선정 |
| 수집 기간 | 선택 | 뉴스·공시. 미입력 시 최근 12개월(뉴스), 180일(공시) |

**티커를 확정하지 못하면 에이전트 실행 전 사용자에게 먼저 묻는다.**

**환경 변수:** `SEC_USER_AGENT="이름 연락처"` — SEC EDGAR는 연락처가 포함된 User-Agent를 요구한다. 설정돼 있지 않으면 사용자에게 설정을 안내하고(예: `setx SEC_USER_AGENT "Your Name you@example.com"`), 임시로 실행할 때는 명령에 `SEC_USER_AGENT=... ` 접두를 붙인다. **사용자 이메일을 임의로 SEC에 보내지 않는다 — 사용자가 알려준 값만 사용.**

---

## 출력 경로
`C:/claude/stock/US/{TICKER}/{YYYYMMDD}/` 아래에 서브폴더로 통합 관리:

| 에이전트 | 폴더 |
|----------|------|
| us-financial-agent | `financial/` |
| us-analyst-news-agent | `analyst/`, `news/` |
| us-industry-macro-agent | `industry/` |
| us-valuation-agent | `valuation/` |
| us-final-report-agent | `final/` |

---

## 병렬 실행 방법

파라미터 확인 후 **단일 응답에서 Agent 도구 3개(Agent 1~3)를 동시에 호출**한다. Agent 4는 1~3 완료 후, Agent 5는 1~4 완료 후 실행한다.

### Agent 1: us-financial-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/us-stock/us-financial-agent
  CLAUDE.md(C:/claude/stock/us-stock/us-financial-agent/CLAUDE.md)의 지침에 따라 SEC 재무 분석을 수행하라.
  - 티커: {TICKER}
  - 기업명: {기업명}
  - 분석일자: {YYYYMMDD}
  - 출력: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/financial/
```

### Agent 2: us-analyst-news-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/us-stock/us-analyst-news-agent
  CLAUDE.md(C:/claude/stock/us-stock/us-analyst-news-agent/CLAUDE.md)의 지침에 따라 시세·월가 컨센서스·뉴스 분석을 수행하라.
  - 티커: {TICKER}
  - 기업명: {기업명}
  - 분석일자: {YYYYMMDD}
  - 수집 기간: {기간 또는 미입력(최근 12개월)}
  - 출력: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/analyst/ , .../news/
```

### Agent 3: us-industry-macro-agent
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/us-stock/us-industry-macro-agent
  CLAUDE.md(C:/claude/stock/us-stock/us-industry-macro-agent/CLAUDE.md)의 지침에 따라 산업·거시 분석을 수행하라.
  - 티커: {TICKER}
  - 기업명: {기업명}
  - 분석일자: {YYYYMMDD}
  - 업종 태그: {태그 또는 미입력(자동 분류)}
  - 경쟁사 티커: {티커들 또는 미입력}
  - 출력: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/industry/
```

### Agent 4: us-valuation-agent (Agent 1~3 완료 후)
```
subagent_type: claude
run_in_background: true
prompt:
  작업 디렉토리: C:/claude/stock/us-stock/us-valuation-agent
  CLAUDE.md(C:/claude/stock/us-stock/us-valuation-agent/CLAUDE.md)의 지침에 따라 비즈니스모델·밸류에이션·SEC 공시 분석을 수행하라.
  - 티커: {TICKER}
  - 기업명: {기업명}
  - 분석일자: {YYYYMMDD}
  - base_path: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/
```

### Agent 5: us-final-report-agent (Agent 1~4 완료 후)
```
subagent_type: claude
run_in_background: false
prompt:
  작업 디렉토리: C:/claude/stock/us-stock/us-final-report-agent
  CLAUDE.md(C:/claude/stock/us-stock/us-final-report-agent/CLAUDE.md)의 지침에 따라 최종 종합 리포트를 생성하라.
  - 티커: {TICKER}
  - 기업명: {기업명}
  - 분석일자: {YYYYMMDD}
  - base_path: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/
```

**실패 처리 정책 (Agent 5 실행 전):**
- 필수(financial, valuation) 실패 → 사용자에게 확인 후 실행
- 선택(analyst-news, industry-macro) 실패 → 사용자에게 알린 후 자동 진행 (확률 앵커는 기본값 30/50/20)

---

## 실행 규칙
- Agent 1~3 병렬, Agent 4는 1~3 완료 후, Agent 5는 1~4 완료 후. 각 에이전트는 독립 실행 — 한쪽 실패가 다른 쪽에 영향 없음.
- 모든 금액은 **USD**, 단위는 에이전트가 JSON에 명시(재무: USD millions, 주당: USD).
- **수치마다 출처 표기**(`← SEC 10-Q`, `← StockAnalysis`, `← Freddie Mac` 등). 소스 간 충돌은 임의 조정하지 않고 병기.
- 투자 권유 표현 금지. 면책 문구 포함.
- 도구 장애(예: yfinance rate limit)는 대체 소스로 우회하고 리포트의 "데이터 한계"에 기록.
- **스크립트 실행은 `uv run python -I`(격리 모드) 또는 `uv run`**, 한글 출력은 `-X utf8`(주의: `-I`는 PYTHONUTF8 환경변수를 무시하므로 반드시 `-X utf8`를 함께 사용). docx 생성은 `uv run --with python-docx`.

---

## 완료 보고 형식
```
## 미국 주식 종합 분석 완료: {기업명} ({TICKER})

- 분석일: {YYYYMMDD} | 시세 기준: {종가일} 종가 ${price}
- 에이전트: financial / analyst-news / industry-macro / valuation / final — 각각 완료·실패
- 가중 평균 적정가: ${mid} (적정 범위 ${low}~${high}, {upside}%) | 현재 위치: {저평가/적정 범위/고평가}
- 애널리스트: {Buy/Hold/Sell 분포}, 평균 목표가 ${avg}
- 시나리오: Positive {X}% / Base {Y}% / Negative {Z}%
- 산출물: C:/claude/stock/US/{TICKER}/{YYYYMMDD}/final/
  - integrated_{날짜}_{TICKER}.json
  - report_{날짜}_{TICKER}.md
  - report_{날짜}_{TICKER}.docx
- 데이터 한계: {요약}
```

---

## 디렉토리 구조
```
C:/claude/stock/us-stock/
├── CLAUDE.md                           ← 이 파일 (미국 주식 오케스트레이터)
├── us-financial-agent/                 ← SEC XBRL 재무 (sec-fetcher/fetch_sec.py)
├── us-analyst-news-agent/              ← 시세·월가 컨센서스·뉴스 (market-data/fetch_quote.py)
├── us-industry-macro-agent/            ← 산업·거시·동종사 (macro-collector/fetch_fred.py)
├── us-valuation-agent/                 ← 비즈니스모델·밸류에이션·SEC 공시
│   └── .claude/skills/valuation-engine/scripts/calculate_valuation.py
│   └── .claude/skills/filings-monitor/scripts/fetch_filings.py
├── us-final-report-agent/              ← 통합 리포트 (scenario-builder, validate_report, docx)
└── examples/KBH_20261025/              ← 회귀 테스트용 실제 산출물 예시 (KB Home)

C:/claude/stock/US/{TICKER}/{YYYYMMDD}/   ← 실행 시 생성되는 산출물
  financial/ analyst/ news/ industry/ valuation/ final/
```
