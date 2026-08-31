# 비즈니스모델 분석·밸류에이션·공시 모니터링 Agent 설계서

> **문서 목적**: Claude Code에서 구현 시 참조할 계획서  
> **작성 기준**: DART MCP + korea-stock MCP + 웹 검색 병합 분석  
> **분석 범위**: 비즈니스모델(Price·Quantity·Cost) + 5종 밸류에이션 + 주요 수시공시 모니터링  
> **출력 폴더**: `C:/claude/stock/{기업명}/{날짜}/valuation/`
> **설계서 버전**: v1.1 (인터뷰 반영)

---

## 1. 작업 컨텍스트 문서

### 1.1 배경 및 목적

주식 분석 멀티에이전트 시스템의 **다섯 번째 서브에이전트**로, 기업의 돈 버는 구조(비즈니스모델), 내재가치 추정(밸류에이션), 최근 공시 이벤트를 분석한다. 앞선 네 에이전트(재무실적·증권사 리포트·뉴스 사건·산업 방향성)가 완료된 후 **오케스트레이터에 의해 자동 트리거**되며, 그 산출물(재무 JSON, 텔레그램 콘센서스)을 주요 입력으로 재사용한다. 이 에이전트는 **"지금 이 주식은 얼마짜리인가"** 라는 핵심 질문에 정량적으로 답한다.

**이 에이전트가 답하는 핵심 질문:**
- 이 기업은 어떻게 돈을 버는가? (Price·Quantity·Cost 구조)
- 5가지 방법으로 추정한 내재가치 범위는 어디인가?
- 현재 주가는 내재가치 대비 고평가인가, 저평가인가?
- 증권사 콘센서스 목표주가 대비 LLM 추정은 어떻게 다른가?
- 최근 공시 중 투자 판단에 영향을 줄 수 있는 이벤트가 있는가?

**앞선 에이전트와의 데이터 연계:**

| 에이전트 | 재사용 데이터 | 용도 |
|---------|------------|------|
| financial-analysis-agent | EPS, EBITDA, FCF, BPS, 재무제표 3개년 | val_inputs 파라미터 |
| telegram-report-agent | 증권사 목표주가 목록, 컨센서스 EPS | DCF 성장률 시나리오, 콘센서스 비교표 |
| industry-analysis-agent | industry_classification.json (업종 태그) | 밸류에이션 가중치 자동 설정 |
| news-analysis-agent | (직접 연계 없음 — 공시는 DART MCP 직접 수집) | — |

> **WACC 재현성 원칙:** WACC 구성요소(무위험수익률·베타·시장프리미엄)는 분석 시점 최신 데이터를 반영하며 재현성을 의도적으로 포기한다. val_inputs JSON의 가정 스냅샷으로 사후 추적 가능.

### 1.2 입출력 정의

| 구분 | 항목 | 설명 |
|------|------|------|
| **입력** | 기업명 (필수) | 분석 대상 |
| **입력** | 종목코드 (필수) | DART·korea-stock MCP 호출 기준 |
| **입력** | 앞선 4개 에이전트 산출물 경로 | 오케스트레이터가 전달 |
| **입력** | 공시 모니터링 기간 (선택) | 기본값: 최근 1년 |
| **출력** | 출력 폴더 | `C:/claude/stock/{기업명}/{날짜}/valuation/` |
| **출력** | 비즈니스모델 JSON | `biz_model_{날짜}_{기업명}.json` |
| **출력** | 밸류에이션 입력 데이터 JSON | `val_inputs_{날짜}_{기업명}.json` |
| **출력** | 밸류에이션 결과 JSON | `val_results_{날짜}_{기업명}.json` |
| **출력** | 공시 데이터 JSON | `disclosures_{날짜}_{기업명}.json` |
| **출력** | 분석 마크다운 리포트 | `report_{날짜}_{기업명}.md` |
| **출력** | 분석 Word 리포트 | `report_{날짜}_{기업명}.docx` |

### 1.3 분석 3대 파트

**파트 A: 비즈니스모델 분석 (Price · Quantity · Cost)**

| 축 | 분석 내용 |
|----|----------|
| **Price** | 주요 제품·서비스별 단가 구조, 가격 결정력(Pricing Power), 가격 트렌드 |
| **Quantity** | 판매량·고객 수·시장 침투율, 핵심 볼륨 드라이버, 성장 레버 |
| **Cost** | 매출원가 구조(고정비·변동비), 주요 비용 항목, 레버리지 효과, 원가 경쟁력 |

추가 분석: 수익모델 유형 분류(구독/거래/라이선스/프로젝트 등), 핵심 경쟁 우위(Moat), 사업부문별 수익 기여도

**파트 B: 밸류에이션 (5종)**

> **SOTP 제거 사유:** DART 연결재무제표에 세그먼트별 실적을 공개하는 한국 상장사가 드물어 대부분 청산가치 대체로 적용되며, 분석 품질이 낮아 5종에서 제외.

| 방법 | 핵심 산출물 |
|------|-----------|
| DCF | 적정 주가, 민감도 분석 (콘센서스 있으면 비관/기준/낙관 3행, 없으면 WACC±1%/성장률±1%) |
| PER / PBR / PSR | 업종 평균 배수 대비 현재 배수, 적정가 범위 |
| EV/EBITDA | 기업가치 배수 비교, 동종업계 프리미엄·디스카운트 |
| DDM | 배당 지속 가능성, 고든 성장 모델 기반 적정가 (배당 이력 3년 이상 시만 적용) |
| RIM | 잔여이익 기반 적정가, ROE·자기자본비용 민감도 |

**밸류에이션 가중치 — 업종 태그 기반 동적 조정:**

| 업종 태그 | DCF | PER·PBR·PSR·EV/EBITDA | DDM | 적용 원칙 |
|---------|-----|----------------------|-----|---------|
| 성장주 (바이오·IT·플랫폼) | 50% | 50% | 미적용 | FCF 불안정 → DCF 비중 상향, DDM 제외 |
| 성숙주 (제조·소재·유통) | 40% | 40% | 20% | 균형 배분 |
| 배당·금융주 (리츠·은행·보험) | 30% | 30% | 40% | DDM·PBR 중심 |
| 기타 (LLM 자율 판단) | LLM 재가중 | — | — | 위 태그 미해당 시 LLM이 근거와 함께 설정 |

> DDM 적용 불가 시(배당 이력 3년 미만): DDM 가중치를 DCF 또는 상대가치에 재분배. LLM이 업종 특성에 따라 판단하고 val_inputs JSON에 `weight_rationale` 기록.

**파트 C: 공시 모니터링**

최근 1년 내 주요 수시공시 중 아래 유형 해당 시 중요도 평가:

| 공시 유형 | 모니터링 이유 |
|----------|-------------|
| 대규모 계약 체결·해지 | 매출 변화 직접 영향 |
| 유상증자·전환사채 발행 | 주가 희석, 자본 구조 변화 |
| 자사주 취득·소각 | 주주환원, 수급 신호 |
| 임원 변동 (대표이사·CFO) | 경영 방향성 변화 신호 |
| 소송·제재·과징금 | 잠재 손실, 평판 리스크 |
| 영업양수도·분할·합병 | 구조적 사업 변화 |
| 최대주주 변동·지분 변화 | 지배구조 리스크 |
| 실적 전망 수정 (profit warning) | 컨센서스 하향 신호 |

### 1.4 주요 제약조건

- DCF·RIM 등 추정 기반 밸류에이션은 가정에 따라 결과가 크게 달라짐 → 반드시 주요 가정을 명시하고 민감도 범위로 표현
- 밸류에이션 수치는 스크립트가 계산, LLM은 가정 설정·결과 해석만 담당
- WACC 재현성은 의도적으로 포기 — 분석 시점 최신 무위험수익률·베타를 항상 사용
- DDM은 배당 이력 3년 이상 기업에만 적용. 미충족 시 "적용 불가" 명기 후 가중치 재분배
- 최소 4종 이상 계산 완료가 성공 기준 (DDM 미적용 시 4종 DCF·PER·EV/EBITDA·RIM으로 충족 가능)
- 콘센서스 데이터 미수집 시 DCF 성장률은 DART 과거 CAGR 기준으로 설정하며 리포트에 명기

### 1.5 용어 정의

| 용어 | 정의 |
|------|------|
| WACC | Weighted Average Cost of Capital, 가중평균자본비용 |
| DCF | Discounted Cash Flow, 미래 현금흐름을 현재가치로 할인 |
| EV | Enterprise Value = 시가총액 + 순차입금 |
| EBITDA | 세전·이자·감가상각 전 이익 |
| RIM | Residual Income Model, 잔여이익모형 |
| DDM | Dividend Discount Model, 배당할인모형 |
| Pricing Power | 기업이 비용 상승분을 가격에 전가할 수 있는 능력 |
| industry_tag | 업종 분류 태그. industry-analysis-agent Step 0 확인 결과를 상속하며 별도 재확인 없음 |
| 콘센서스 | telegram-report-agent가 수집한 증권사 목표주가·EPS 추정치 |

---

## 2. 워크플로우 정의

### 2.1 전체 흐름

```
[오케스트레이터: 4개 에이전트 완료 감지]
        │  전달: 기업명, 종목코드, 4개 에이전트 산출물 폴더 경로
        ▼
[Step 0] 출력 폴더 생성 + 앞선 에이전트 산출물 경로 확인
        │
        ▼
[Step 1] 기초 데이터 수집
   재무 에이전트 JSON: EPS·EBITDA·FCF·BPS (재수집 없음)
   텔레그램 에이전트 JSON: 증권사 콘센서스 목표주가·EPS
   industry-analysis-agent: industry_tag 상속 (재확인 없음)
   korea-stock MCP: 현재주가·시총·배당·멀티플 (직접 호출)
   DART MCP: 수시공시 목록 (직접 호출)
   웹 검색: 동종업계 멀티플, 무위험수익률, 베타
        │
        ▼
[Step 2] 비즈니스모델 LLM 분석
   Price·Quantity·Cost 구조화 분석
   → biz_model_{날짜}_{기업명}.json 저장
        │
        ▼
[Step 3] 밸류에이션 입력값 준비
   스크립트: 재무 파라미터 계산 (재무 에이전트 JSON 파서)
   LLM: industry_tag 기반 업종 태그 설정 → 가중치 결정 + WACC 가정
   → val_inputs_{날짜}_{기업명}.json 저장
        │
        ▼
[Step 4] 5종 밸류에이션 계산
   스크립트: DCF·PER·EV/EBITDA·DDM(조건부)·RIM 계산
   → val_results_{날짜}_{기업명}.json 저장
        │
        ▼
[Step 5] 공시 모니터링 분석
   DART MCP 수시공시 → 중요도 평가
   → disclosures_{날짜}_{기업명}.json 저장
        │
        ▼
[Step 6] LLM 종합 분석
   3개 파트 통합, 콘센서스 vs LLM 비교, 현재 주가 위치 해석
        │
        ▼
[Step 7] 문서 생성
   Python → md 생성
   Node.js (generate_docx.js) → docx 생성
        │
        ▼
[출력: C:/claude/stock/{기업명}/{날짜}/valuation/ 내 전체 산출물]
```

### 2.2 단계별 상세 정의

---

#### Step 0: 출력 폴더 생성 + 선행 에이전트 산출물 확인

**처리 주체:** 스크립트 (`setup_dirs.py`)

```
C:/claude/stock/{기업명}/{날짜}/valuation/
  (모든 JSON·리포트 산출물 직접 저장)
```

**선행 에이전트 경로 확인:**
오케스트레이터가 전달하는 4개 에이전트 산출물 폴더 경로가 모두 존재하는지 검증.

```
필수 경로 확인:
  C:/claude/stock/{기업명}/{날짜}/financial/    → EPS·EBITDA·FCF JSON
  C:/claude/stock/{기업명}/{날짜}/telegram/     → 콘센서스 JSON
  C:/claude/stock/{기업명}/{날짜}/industry/     → industry_tag JSON
  (news 경로는 직접 연계 없음)
```

**성공 기준:** 폴더 생성 완료, 재무·텔레그램·산업 에이전트 경로 존재 확인  
**실패 처리:** 경로 미존재 시 → 해당 에이전트 데이터 없음으로 표시 후 MCP 직접 수집으로 대체

---

#### Step 1: 기초 데이터 수집

**처리 주체:** 선행 에이전트 JSON 파서 + korea-stock MCP + DART MCP + 웹 검색

**선행 에이전트 JSON에서 읽는 항목 (재수집 불필요):**

| 출처 에이전트 | 수집 항목 | val_inputs 매핑 |
|------------|---------|---------------|
| financial-analysis-agent | EPS (TTM·예상), EBITDA, FCF, 자기자본, BPS, 순차입금 | `financials.*` |
| financial-analysis-agent | 최근 3~5개년 손익·현금흐름 (밸류에이션 계산용) | `financials.history` |
| telegram-report-agent | 증권사별 목표주가 목록, 평균 컨센서스 EPS | `consensus.*` |
| industry-analysis-agent | industry_tag (예: "성장주_반도체") | `industry_tag` |

> **통합 산출물 경로:** 앞선 4개 에이전트는 모두 `C:/claude/stock/{기업명}/{YYYYMMDD}/` 하위 서브폴더에 저장.
> - financial: `C:/claude/stock/{기업명}/{YYYYMMDD}/financial/`
> - telegram: `C:/claude/stock/{기업명}/{YYYYMMDD}/telegram/`
> - industry: `C:/claude/stock/{기업명}/{YYYYMMDD}/industry/`
> - news: `C:/claude/stock/{기업명}/{YYYYMMDD}/news/`

**financial-analysis-agent JSON 파서 (`read_financial_agent.py`):**
- 재무 에이전트의 기존 JSON 키 구조를 그대로 읽어 val_inputs 스키마로 변환
- 매핑 기준 문서: `references/financial_agent_field_map.md`

**korea-stock MCP 직접 호출 항목 (재무 에이전트 미포함):**
- 현재 주가, 52주 최고·최저가
- 시가총액, 발행주식수, 유동주식수
- 현재 PER, PBR, PSR, EV/EBITDA (시장 계산 기준)
- 최근 3년 배당금·배당수익률·배당성향
- 외국인·기관 보유 비율 및 최근 6개월 수급 추이
- 동종업계 주요 기업 멀티플 (비교 대상 3~5개)

**DART MCP 직접 호출 항목:**
- 수시공시 목록 (최근 1년, 공시 유형·날짜·제목·원문 링크)
- 재무 에이전트 미수집 항목 (감가상각비, CapEx, 우발부채 주석)

**웹 검색 수집 항목:**
- 업종 평균 PER·EV/EBITDA 최신 자료
- 무위험수익률(국고채 10년물), 시장 리스크 프리미엄, 베타값

**분기조건:**
```
재무 에이전트 JSON 존재?
  ├─ YES → JSON 파서로 읽기
  └─ NO  → DART MCP로 직접 재무제표 수집, 리포트에 "선행 에이전트 데이터 미사용" 명시

텔레그램 에이전트 콘센서스 존재?
  ├─ YES → consensus.* 필드 채우기, DCF 민감도 3행 구성
  └─ NO  → consensus 필드 null, DCF 성장률 DART CAGR 기준, 민감도 WACC±1%/성장률±1%

콘센서스 낙관 편향 감지 (컨센서스 평균이 DART CAGR 2배 초과)?
  └─ 리포트 Step 6에 "콘센서스 낙관 편향 가능성" 경고 삽입
```

**성공 기준:**
- 재무제표 3개년 이상 확보
- 현재 주가 및 시가총액 확보

---

#### Step 2: 비즈니스모델 LLM 분석

**처리 주체:** 에이전트 직접 수행 (LLM 판단 영역)

**분석 프레임워크 — Price · Quantity · Cost:**

```
[Price 분석]
- 주요 제품·서비스별 가격대 및 단가 수준
- 가격 결정 구조: 시장가 연동 / 협상 / 구독 / 프리미엄 등
- 가격 결정력(Pricing Power): 원가 상승분 전가 가능 여부
- 최근 3년 ASP(평균판매단가) 트렌드
- 가격 리스크: 경쟁 압력·규제·원자재 가격 연동 여부

[Quantity 분석]
- 핵심 판매 단위: 대수·건수·가입자·처리량 등
- 최근 3년 볼륨 추이 및 성장률
- 핵심 볼륨 드라이버 (무엇이 판매량을 결정하는가)
- 시장 침투율 및 성장 여력
- 고객 집중도: 상위 10개 고객 매출 비중 (공개 시)

[Cost 분석]
- 매출원가 구조: 원재료비·노무비·감가상각비 비중
- 고정비 vs 변동비 비율 → 영업 레버리지 수준
- 주요 원가 항목별 가격 민감도
- 판관비 구조: R&D·마케팅·인건비 추이
- 원가 경쟁력: 규모의 경제·수직계열화·지역 비용 우위

[수익모델 분류]
- 수익 유형: 제품판매·서비스구독·라이선스·프로젝트·중개 등
- 반복성 매출(Recurring Revenue) 비중
- 사업부문별 매출·영업이익 기여도 및 마진 격차

[핵심 경쟁 우위 (Moat)]
- 전환비용·네트워크효과·규모의경제·무형자산·비용우위 중 해당 항목
- 경쟁 우위의 지속 가능성 평가 (5년 이상 유지 가능한가)
```

**성공 기준 (LLM 자기 검증):**
- Price·Quantity·Cost 3축 모두 서술 존재
- 각 축에 최소 3개 이상 구체 항목 포함
- 수치 인용 시 출처(사업보고서 연도·웹 소스) 명시
- Moat 평가에 근거 기술

**실패 처리:** 자기 검증 실패 → 해당 축 재작성 1회

---

#### Step 3: 밸류에이션 입력값 준비

**처리 주체:** 스크립트 (정량 계산) + LLM (가정 설정)

**스크립트 처리 (`prepare_val_inputs.py`):**
- 재무 에이전트 JSON 파서 (`read_financial_agent.py`) 호출
- 추가 계산: NOPAT, 순차입금, FCF 마진, 최근 3년 평균 ROE·ROA·영업이익률
- 베타 소스: korea-stock MCP → 없으면 웹 검색

**LLM 가정 설정 (에이전트 직접 수행):**

| 가정 항목 | 설정 기준 |
|----------|----------|
| industry_tag | industry-analysis-agent 결과 상속 (재확인 없음) |
| 밸류에이션 가중치 | industry_tag 기반 표 조회 → weight_rationale과 함께 JSON 기록 |
| 무위험수익률 | 수집된 국고채 10년물 금리 사용 (매번 최신 적용) |
| 시장 리스크 프리미엄 | 한국 시장 기준 5~6% 범위, 수집 데이터 우선 |
| 베타 | korea-stock MCP 값, 없으면 업종 평균 |
| WACC | CAPM 기반 자기자본비용 + 세후 타인자본비용 |
| FCF 성장률 | 콘센서스 EPS CAGR 우선 → 없으면 DART FCF CAGR; 산업 전망 반영 조정 |
| 영구 성장률 | GDP 성장률 수준 (1.5~2.5% 범위) |
| 적정 배수 기준 | 동종업계 평균 멀티플 (수집된 데이터 기준) |

> **원칙:** 모든 가정은 근거 데이터와 함께 `val_inputs` JSON에 기록. 가정 없이 계산 진행 금지.

**성공 기준:** 모든 필수 파라미터 존재, 가정 근거 명시 완료

---

#### Step 4: 5종 밸류에이션 계산

**처리 주체:** 스크립트 (`calculate_valuation.py`)

**각 방법별 계산 로직:**

**① DCF (현금흐름할인)**
```
- 단기 FCF 예측: 5년, 설정된 성장률 적용
  - 콘센서스 있을 때: 비관/기준/낙관 3개 시나리오 (콘센서스 EPS 범위에서 파생)
  - 콘센서스 없을 때: DART CAGR 기준 단일 성장률
- 터미널 밸류: Gordon Growth Model (영구 성장률 적용)
- 할인율: WACC
- 산출: 주당 내재가치 + 민감도 테이블
  - 콘센서스 있을 때: 비관/기준/낙관 3행 (WACC 고정, 성장률 시나리오 변동)
  - 콘센서스 없을 때: WACC±1% × 성장률±1% 2×2 테이블 (5행)
```

**② PER / PBR / PSR (상대가치)**
```
- PER: 동종업계 평균 PER × 예상 EPS → 적정 주가
- PBR: 동종업계 평균 PBR × BPS → 적정 주가
- PSR: 동종업계 평균 PSR × 주당 매출 → 적정 주가
- 산출: 3가지 배수별 적정가 + 현재 배수 vs 업종 평균 비교표
```

**③ EV/EBITDA**
```
- 동종업계 평균 EV/EBITDA × 자사 EBITDA → 적정 EV
- 적정 EV - 순차입금 → 적정 시가총액 → 주당 적정가
- 산출: 적정가 + 업종 EV/EBITDA 비교표
```

**④ DDM (배당할인모형)**
```
- 배당 이력 확인: 최근 3년 DPS, 배당 성향 추이
- 적용 조건: 배당 이력 3년 이상 + 배당성향 안정적
- Gordon Growth: P = DPS₁ / (Ke - g)
- 산출: 적정 주가 + 적용 불가 시 사유 명기 → 가중치 재분배
```

**⑤ RIM (잔여이익모형)**
```
- 잔여이익 = 순이익 - (자기자본 × 자기자본비용)
- 현재 자기자본 + 미래 잔여이익 PV 합산
- 산출: 적정 주가 + ROE vs 자기자본비용 민감도 분석
```

**통합 결과 산출:**
- 적용 가능 방법별 적정 주가 범위 → 최소·중간·최대값
- 업종 태그 기반 가중 평균 적정가
- 현재 주가 대비 upside/downside % 계산

**성공 기준:**
- 적용 가능한 방법 최소 4종 계산 완료
- 각 방법의 입력값·가정이 `val_inputs` JSON에 존재
- 민감도 분석 테이블 (DCF·RIM 최소 1종)

**실패 처리:**
- 특정 방법 계산 오류 → 해당 방법 스킵 + 로그 기록, 나머지 진행
- 4종 미만 계산 가능 → 리포트에 한계 명시

---

#### Step 5: 공시 모니터링 분석

**처리 주체:** 에이전트 직접 수행 (LLM 판단 영역)

**입력:** DART MCP 수집 수시공시 목록 (최근 1년)

**각 공시에 대해 추출·평가할 항목:**

```json
{
  "disclosure_date": "YYYY-MM-DD",
  "disclosure_type": "공시 유형",
  "title": "공시 제목",
  "dart_url": "원문 링크",
  "importance": "high | medium | low",
  "investment_impact": "positive | negative | neutral",
  "summary": "투자자 관점 한 줄 요약 (50자 이내)",
  "detail": "상세 설명 (200자 이내, 수치 포함)",
  "action_required": true,
  "monitoring_note": "향후 주목할 후속 일정 또는 리스크"
}
```

**중요도 판단 기준 (LLM 지침):**

| 중요도 | 기준 |
|--------|------|
| **high** | 주가 5% 이상 영향 가능성, 사업 구조 변화, 지배구조 변동 |
| **medium** | 계약·소송 등 주목 필요하나 즉각 영향 제한적 |
| **low** | 정기적 공시, 소규모 변동, 형식적 보고 |

**성공 기준 (LLM 자기 검증):**
- 모든 공시에 `importance` · `investment_impact` 부여
- `high` 판정 공시에 `detail` 필드 충실히 기술
- 원문 없이 중요도 판단 금지 (원문 링크 필수)

**실패 처리:**
- 공시 0건 → "해당 기간 내 주요 수시공시 없음" 기록 후 진행
- 공시 원문 fetch 실패 → 제목 기반 평가, `confidence: low` 표기

---

#### Step 6: LLM 종합 분석

**처리 주체:** 에이전트 직접 수행 (LLM 판단 영역)

**분석 구조:**

```
1. 비즈니스모델 핵심 요약
   - Price·Quantity·Cost 각 축의 핵심 특성 한 단락
   - 수익 구조의 강점과 취약점
   - Moat 평가 결론

2. 밸류에이션 종합
   2-A. 5종 방법별 적정가 비교 테이블
        (방법 / 적정가 하단 / 중간 / 상단 / 현재주가 대비 %)
   2-B. [별도 섹션] 증권사 콘센서스 vs LLM 추정 비교표
        콘센서스 수집 시:
          | 증권사 | 목표주가 | EPS 추정 | 리포트 날짜 |
          + LLM DCF 기준 추정치 행 추가
        콘센서스 미수집 시:
          "텔레그램 에이전트 데이터 미수집 — 콘센서스 비교 불가" 명기 후 빈 표
        콘센서스 낙관 편향 감지 시:
          "증권사 컨센서스가 DART CAGR 대비 XX% 높음 — 낙관 편향 가능성" 경고
   2-C. 업종 태그 및 가중치 결정 근거
        "industry_tag: {태그} → DCF {X}% / 상대가치 {Y}% / DDM {Z}%"
   2-D. 가중 평균 적정가 및 목표가 범위
   2-E. 현재 주가 위치 해석:
        "현재 주가 {X}원은 5종 밸류에이션 중간값 {Y}원 대비 {Z}% {고평가/저평가}"
   2-F. 밸류에이션 방법 간 괴리가 큰 경우 원인 설명

3. 공시 이벤트 요약
   - high 중요도 공시 목록 및 투자 영향
   - 진행 중인 이슈 (소송·증자 등 미완결 이벤트)
   - 향후 주목할 공시 일정

4. 종합 투자 관점 요약
   - 비즈니스모델 관점: 돈 버는 구조가 튼튼한가?
   - 밸류에이션 관점: 현재 가격이 합리적인가?
   - 공시 관점: 현재 리스크 이벤트가 있는가?
   - 3개 관점 종합 한 단락 (투자의견 단언 금지, 근거 중심 서술)
```

> **금지 사항:** "매수하세요", "지금 사야 합니다" 등 투자 권유 표현 금지.  
> 모든 서술은 "~로 판단됨", "~가능성 있음" 등 근거 기반 서술 유지.

**성공 기준 (LLM 자기 검증):**
- 2-A~F, 3, 4 모든 섹션 존재
- 밸류에이션 비교 테이블에 5종 방법 모두 행 존재 (적용 불가 시 사유 기재)
- 콘센서스 섹션 항상 존재 (수집 실패 시 "미수집" 명기)
- 투자 권유 표현 없음

---

#### Step 7: 문서 생성

**처리 주체:** Python 스크립트 (`generate_md.py`) + Node.js 스크립트 (`generate_docx.js`)

**마크다운 리포트 (.md):**
- Step 6 분석 전체 텍스트
- 밸류에이션 비교 테이블 마크다운 형식
- 콘센서스 비교표 마크다운 형식
- `output/report_{날짜}_{기업명}.md` 저장

**Word 리포트 (.docx):**
- 생성 도구: `docx` npm 라이브러리 (`/report-builder/scripts/package.json` 관리)
- Python `generate_report.py`가 `subprocess`로 `node generate_docx.js` 호출
- 표지 (기업명, 분석일자, 현재 주가, 가중 평균 적정가, industry_tag)
- 목차 자동 생성
- 밸류에이션 비교 테이블: 색상 강조 (현재주가가 적정가 하단 이하 → 초록, 상단 이상 → 빨강)
- DCF 민감도 테이블 포함 (콘센서스/WACC 기반 조건부 형식)
- 콘센서스 vs LLM 비교표 별도 섹션
- 공시 목록: 중요도별 색상 구분 (high: 빨강, medium: 노랑, low: 회색)
- `output/report_{날짜}_{기업명}.docx` 저장

**성공 기준:** 두 파일 모두 존재, docx 유효성 검증 통과  
**실패 처리:** docx 생성 실패 → md만 최종 산출, 오류 로그 기록

---

### 2.3 LLM 판단 영역 vs 코드 처리 영역 요약

| 단계 | 처리 주체 | 이유 |
|------|----------|------|
| 선행 에이전트 JSON 파싱 | 스크립트 | 결정론적 필드 추출 |
| korea-stock MCP·DART MCP 수집 | MCP 도구 | 외부 API 호출 |
| 재무 파라미터 계산 | 스크립트 | 결정론적 수식 처리 |
| 비즈니스모델 구조화 분석 | **LLM** | 사업보고서 맥락 기반 판단 |
| industry_tag 확인 + 가중치 결정 | **LLM** (industry 에이전트 상속) | 가중치 테이블 조회 + 예외 판단 |
| WACC·성장률 가정 설정 | **LLM** | 근거 데이터 해석 + 판단 |
| 5종 밸류에이션 수치 계산 | 스크립트 | 수식 기반 반복 처리, 오계산 방지 |
| DCF 민감도 형식 선택 | 스크립트 (콘센서스 유무 분기) | 조건 기반 포맷 전환 |
| 밸류에이션 결과 해석 | **LLM** | 방법 간 괴리 원인, 적정가 위치 판단 |
| 콘센서스 낙관 편향 감지 | **LLM** | 수치 비교 후 서술 판단 |
| 공시 중요도·투자 영향 평가 | **LLM** | 맥락 기반 정성 판단 |
| 종합 투자 관점 서술 | **LLM** | 3개 파트 교차 종합 |
| md/docx 문서 생성 | 스크립트 (Python + Node.js) | 파일 I/O |

---

## 3. 구현 스펙

### 3.1 폴더 구조

```
C:/claude/stock/valuation-agent/
  ├── CLAUDE.md                                  # 메인 에이전트 지침
  ├── /.claude
  │   └── /skills
  │       ├── /data-collector                    # 데이터 수집 스킬
  │       │   ├── SKILL.md
  │       │   ├── /scripts
  │       │   │   ├── collect_data.py            # korea-stock MCP·DART·웹 보완 수집
  │       │   │   └── read_financial_agent.py    # 재무 에이전트 JSON 파서
  │       │   └── /references
  │       │       ├── dart_field_map.md          # DART 주석 항목 매핑 가이드
  │       │       ├── korea_stock_mcp_guide.md   # korea-stock MCP API 가이드
  │       │       └── financial_agent_field_map.md  # 재무 에이전트 JSON 키 → val_inputs 매핑
  │       ├── /biz-model-analyzer                # 비즈니스모델 분석 스킬
  │       │   ├── SKILL.md
  │       │   └── /references
  │       │       └── pqc_framework.md           # Price·Quantity·Cost 분석 프레임워크
  │       ├── /valuation-engine                  # 밸류에이션 계산 스킬
  │       │   ├── SKILL.md
  │       │   ├── /scripts
  │       │   │   ├── prepare_val_inputs.py      # 파라미터 계산 (read_financial_agent.py 호출)
  │       │   │   └── calculate_valuation.py     # 5종 밸류에이션 계산
  │       │   └── /references
  │       │       ├── valuation_formulas.md      # 5종 공식 정의
  │       │       ├── wacc_guide.md              # WACC 구성요소 및 한국 시장 기준값
  │       │       └── industry_weight_table.md   # 업종 태그별 가중치 기준표
  │       ├── /disclosure-monitor                # 공시 모니터링 스킬
  │       │   ├── SKILL.md
  │       │   └── /references
  │       │       └── disclosure_type_guide.md   # 공시 유형별 중요도 판단 기준
  │       └── /report-builder                    # 문서 생성 스킬
  │           ├── SKILL.md
  │           └── /scripts
  │               ├── setup_dirs.py
  │               ├── generate_md.py
  │               ├── generate_report.py         # md 생성 + subprocess로 docx 호출
  │               ├── package.json               # docx npm 의존성 (Node.js)
  │               └── generate_docx.js           # Word 리포트 생성 (Node.js)
  └── /docs
      └── industry_multiples.md                  # 업종별 적정 배수 참고값 (정기 업데이트)

※ 실행 시 생성되는 출력 폴더:
C:/claude/stock/{기업명}/{날짜}/valuation/
      ├── biz_model_{날짜}_{기업명}.json
      ├── val_inputs_{날짜}_{기업명}.json
      ├── val_results_{날짜}_{기업명}.json
      ├── disclosures_{날짜}_{기업명}.json
      ├── report_{날짜}_{기업명}.md
      └── report_{날짜}_{기업명}.docx
```

> **폴더 위치:** 다른 4개 에이전트와 동일한 `C:/claude/stock/{기업명}/{날짜}/` 하위에 `valuation/` 서브폴더로 통합  
> 예시: `C:/claude/stock/삼성전자/20260602/valuation/`

### 3.2 CLAUDE.md 핵심 섹션 목록

| 섹션 | 내용 요약 |
|------|----------|
| 역할 정의 | 비즈니스모델·밸류에이션·공시 분석 에이전트, 5번째 서브에이전트 |
| 트리거 조건 | 오케스트레이터가 4개 에이전트 완료 후 자동 실행, 4개 에이전트 산출물 경로 수신 |
| 스킬 호출 순서 | setup → collect (선행 JSON 파싱 포함) → biz-model → val-inputs → val-calc → disclosure → synthesize → report |
| 비즈니스모델 분석 원칙 | Price·Quantity·Cost 3축 필수, 수치 기반 서술 |
| 밸류에이션 가정 원칙 | 모든 가정 근거 명시 의무, LLM 직접 계산 금지, WACC 매번 최신 적용 |
| 업종 태그 및 가중치 원칙 | industry-analysis-agent 결과 상속, 재확인 없음, weight_rationale 기록 |
| 공시 중요도 판단 기준 | high/medium/low 기준 및 투자 영향 서술 원칙 |
| 출력 경로 규칙 | `C:/claude/stock/{기업명}/{날짜}/valuation/` |
| 금지 사항 | 투자 권유 표현, LLM 직접 수치 계산, 근거 없는 가정, 업종 재확인 (산업 에이전트 결과 상속) |

### 3.3 에이전트 구조

**단일 에이전트** 구조 채택

**근거:** 비즈니스모델 분석(Step 2)에서 파악한 수익 구조가 밸류에이션 가정 설정(Step 3)에 직접 영향을 주고, 공시 이벤트(Step 5)가 종합 해석(Step 6)에서 비즈니스모델·밸류에이션과 교차 해석되어야 함. 컨텍스트 연속성이 분석 품질의 핵심.

### 3.4 스킬 파일 목록 및 역할

| 스킬명 | 역할 | 트리거 조건 |
|--------|------|-----------|
| `data-collector` | 선행 에이전트 JSON 파싱 + korea-stock·DART·웹 보완 수집 | 워크플로우 시작 시 |
| `biz-model-analyzer` | Price·Quantity·Cost 분석 프레임워크 제공 | 데이터 수집 완료 직후 (LLM 참조용) |
| `valuation-engine` | 파라미터 계산 + 5종 밸류에이션 수치 계산 | 비즈니스모델 분석 완료 직후 |
| `disclosure-monitor` | 공시 중요도 판단 기준 제공 | 밸류에이션 계산 완료 직후 (LLM 참조용) |
| `report-builder` | 폴더 생성 + md/docx 생성 | 종합 분석 완료 직후 |

### 3.5 주요 산출물 파일 형식

**산출물 전체 목록:**

| 파일 | 형식 | 생성 단계 | 설명 |
|------|------|----------|------|
| `biz_model_{날짜}_{기업명}.json` | JSON | Step 2 | Price·Quantity·Cost 구조화 결과 |
| `val_inputs_{날짜}_{기업명}.json` | JSON | Step 3 | 밸류에이션 파라미터·가정·업종 태그·가중치 전체 |
| `val_results_{날짜}_{기업명}.json` | JSON | Step 4 | 5종 계산 결과 및 민감도 테이블 |
| `disclosures_{날짜}_{기업명}.json` | JSON | Step 5 | 공시 목록 및 중요도 평가 |
| `report_{날짜}_{기업명}.md` | Markdown | Step 7 | 종합 분석 리포트 |
| `report_{날짜}_{기업명}.docx` | Word | Step 7 | 종합 분석 리포트 (인쇄용) |

**`val_inputs_{날짜}_{기업명}.json` 스키마 개요:**
```json
{
  "company": "삼성전자",
  "base_date": "2026-06-02",
  "industry_tag": "성숙주_반도체",
  "weight_rationale": "반도체 성숙 사이클 진입, FCF 안정적 → 성숙주 가중치 적용. DDM 적용 (3년 배당 이력 충족)",
  "valuation_weights": {
    "dcf_rim": 0.40,
    "relative": 0.40,
    "ddm": 0.20
  },
  "current_price": 75000,
  "shares_outstanding": 5969782550,
  "market_cap": 447733691250000,
  "data_sources": {
    "financial_agent_path": "C:/claude/stock/삼성전자/20260602/financial/",
    "telegram_agent_path": "C:/claude/stock/삼성전자/20260602/telegram/",
    "industry_agent_path": "C:/claude/stock/삼성전자/20260602/industry/"
  },
  "financials": {
    "ebitda": 45000000000000,
    "nopat": 32000000000000,
    "fcf": 28000000000000,
    "net_debt": -50000000000000,
    "book_value_per_share": 52000,
    "eps_ttm": 8200,
    "dps_last": 1444,
    "revenue_per_share": 55000
  },
  "consensus": {
    "available": true,
    "target_price_list": [
      {"firm": "A증권", "target": 95000, "eps_est": 9500, "date": "2026-05-20"},
      {"firm": "B증권", "target": 102000, "eps_est": 10200, "date": "2026-05-15"}
    ],
    "avg_target_price": 98500,
    "avg_eps_estimate": 9850,
    "fcf_growth_from_consensus": 0.115
  },
  "assumptions": {
    "risk_free_rate": { "value": 0.033, "source": "국고채 10년물 2026-06" },
    "market_risk_premium": { "value": 0.055, "source": "Damodaran 한국 2025" },
    "beta": { "value": 1.15, "source": "korea-stock MCP" },
    "wacc": { "value": 0.089, "calculation": "CAPM 기반, D/E 0.3 반영" },
    "fcf_growth_rate_5y": {
      "value": 0.115,
      "basis": "콘센서스 EPS CAGR 기반 (DART CAGR 15% vs 콘센서스 CAGR 11.5% → 콘센서스 우선)"
    },
    "terminal_growth_rate": { "value": 0.02, "basis": "한국 명목 GDP 성장률 수준" },
    "peer_per": { "value": 15.2, "peers": ["SK하이닉스", "마이크론", "TSMC"], "source": "웹 검색" },
    "peer_ev_ebitda": { "value": 8.5, "source": "웹 검색" }
  }
}
```

**`val_results_{날짜}_{기업명}.json` 스키마 개요:**
```json
{
  "company": "삼성전자",
  "current_price": 75000,
  "dcf_sensitivity_format": "consensus",
  "results": {
    "dcf": {
      "base": 88000,
      "range": { "low": 72000, "high": 108000 },
      "sensitivity": {
        "consensus_bear": 78000,
        "consensus_base": 88000,
        "consensus_bull": 105000
      },
      "upside_pct": 17.3
    },
    "per_relative": { "base": 82000, "range": { "low": 74000, "high": 92000 }, "upside_pct": 9.3 },
    "pbr_relative": { "base": 78000, "range": { "low": 70000, "high": 86000 }, "upside_pct": 4.0 },
    "psr_relative": { "base": 71000, "range": { "low": 64000, "high": 80000 }, "upside_pct": -5.3 },
    "ev_ebitda": { "base": 85000, "range": { "low": 76000, "high": 96000 }, "upside_pct": 13.3 },
    "ddm": { "base": 62000, "applicable": true, "upside_pct": -17.3 },
    "rim": { "base": 84000, "range": { "low": 75000, "high": 95000 }, "upside_pct": 12.0 }
  },
  "weighted_average": { "value": 83500, "upside_pct": 11.3 },
  "fair_value_range": { "low": 74000, "high": 96000 }
}
```

**리포트 문서 구조 (report.md / report.docx 공통):**
```
표지 (기업명, 분석일자, 현재 주가, 가중 평균 적정가, upside%, industry_tag)
목차
1. 비즈니스모델 분석
   1.1 Price 분석
   1.2 Quantity 분석
   1.3 Cost 분석
   1.4 수익모델 분류 및 Moat 평가
2. 밸류에이션
   2.1 업종 태그 및 가중치 결정 근거
   2.2 주요 가정 및 파라미터 (WACC 구성요소 포함)
   2.3 5종 방법별 결과 비교 테이블
   2.4 증권사 콘센서스 vs LLM 추정 비교표
        (미수집 시: "콘센서스 미수집" 명기 + 빈 표)
   2.5 DCF 민감도 분석 (콘센서스 시나리오 또는 WACC±1% 형식)
   2.6 적정가 범위 종합
3. 공시 모니터링
   3.1 주요 공시 목록 (중요도순)
   3.2 진행 중 이슈 및 모니터링 포인트
4. 종합 투자 관점 요약
부록: 밸류에이션 상세 계산 과정 + 선행 에이전트 데이터 소스 명세
```

---

## 4. 오케스트레이터 연동 스펙

### 4.1 트리거 조건

오케스트레이터(C:/claude/stock/CLAUDE.md)는 다음 조건 충족 시 이 에이전트를 자동 실행한다:
- financial-analysis-agent 완료 확인 (산출물 폴더 내 JSON 존재)
- telegram-report-agent 완료 확인
- industry-analysis-agent 완료 확인 (industry_classification.json 존재)
- news-analysis-agent 완료 확인 (직접 데이터 연계 없으나 전체 완료 후 실행)

### 4.2 오케스트레이터 → 에이전트 전달 파라미터

```
- 기업명: {기업명}
- 종목코드: {종목코드}
- base_path: C:/claude/stock/{기업명}/{날짜}/
- financial_agent_path: C:/claude/stock/{기업명}/{날짜}/financial/
- telegram_agent_path: C:/claude/stock/{기업명}/{날짜}/telegram/
- industry_agent_path: C:/claude/stock/{기업명}/{날짜}/industry/
- news_agent_path: C:/claude/stock/{기업명}/{날짜}/news/
```

### 4.3 완료 보고 형식 (오케스트레이터 최종 보고에 추가)

```
### 밸류에이션 분석 (valuation-agent)
- 상태: 완료 / 실패
- 업종 태그: {industry_tag}
- 가중 평균 적정가: {N}원 ({upside_pct}% upside/downside)
- 적용 방법 수: {N}종 (DDM: 적용/미적용)
- 콘센서스 수집: 수집 ({N}개 증권사) / 미수집
- 산출물: `C:/claude/stock/{기업명}/{날짜}/valuation/`
```

---

## 5. 설계 결정 근거 (주요 판단 기록)

| 결정 항목 | 선택 | 근거 |
|----------|------|------|
| 단일 vs 멀티 에이전트 | 단일 에이전트 | 비즈니스모델 이해가 밸류에이션 가정에 직접 연결됨 |
| 밸류에이션 계산 주체 | 스크립트 | LLM의 수치 계산 오류 방지, 재현 가능성 확보 |
| 가정 설정 주체 | LLM | WACC·성장률은 데이터 해석 + 판단 필요 |
| WACC 재현성 | 포기 | 분석 시점 최신 무위험수익률 반영이 정확성에 우선 |
| 밸류에이션 가중치 | LLM이 업종 태그 기반 동적 조정 | 바이오/성장주는 DCF 가중치가 오히려 왜곡, 배당주는 DDM 중심이 맞음 |
| SOTP 제거 | 5종으로 축소 | 한국 상장사 세그먼트 공개 드물어 대부분 청산가치로 대체 → 품질 저하 |
| 4종 최소 기준 유지 | 유지 | DDM 미적용 시 DCF·PER/PBR/PSR·EV/EBITDA·RIM 4종으로 충족 가능 |
| 재무 에이전트 데이터 재사용 | 파서 방식 (재무 에이전트 JSON 포맷 기준) | 재수집 불필요, 재무 에이전트 포맷 변경 시 field_map.md만 업데이트 |
| 업종 확인 중복 제거 | industry-analysis-agent 결과 상속 | 두 에이전트가 각각 업종 확인 시 사용자 부담 과중 |
| 콘센서스 DCF 연동 | 조건부 (콘센서스 있으면 3시나리오, 없으면 WACC±1%) | 데이터가 있으면 더 직관적인 형식 제공 |
| 콘센서스 비교표 | 별도 섹션 (6종 테이블에 행 추가 아님) | 시장 시각과 내재가치 분석을 구분해서 보고 싶은 패턴 반영 |
| docx 생성 | Node.js docx npm | 테이블 색상·스타일 제어가 python-docx보다 유연 |
| 투자 권유 표현 금지 | 강제 | 분석 도구로서의 역할 한계 명확히 |
| 공시 모니터링 범위 | 주요 수시공시 (최근 1년) | 정기공시는 재무 에이전트에서 이미 처리 |

---

*설계서 버전: v1.1 | 이후 종합 리포트 에이전트 설계 시 `val_results_{날짜}_{기업명}.json`의 `weighted_average` 및 `fair_value_range`, `disclosures_{날짜}_{기업명}.json`의 `high` 중요도 공시를 입력 명세로 참조할 것*
