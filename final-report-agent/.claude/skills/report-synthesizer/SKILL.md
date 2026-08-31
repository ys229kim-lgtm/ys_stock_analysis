# report-synthesizer 스킬

## 목적
7개 섹션 작성, 투자 시나리오 도출, Executive Summary 작성, 자기 검증을 수행한다.
모든 작업은 LLM이 직접 수행한다 (코드 처리 불가).

## 참조 파일

| 파일 | 사용 시점 |
|------|---------|
| `references/section_writing_guide.md` | Step 3: 섹션 작성 전반 |
| `references/scenario_guide.md` | Step 4: 시나리오·주가 전망 |
| `references/self_check_list.md` | Step 6: 자기 검증 |

## 컨텍스트 전략

- **Step 2 신호 분석**: `normalized_summary.json` 로드
- **Step 3 섹션 작성**: 섹션마다 해당 원본 JSON **전체 재로드** (정보 손실 방지)
  - 섹션 2: `biz_model_{날짜}_{기업명}.json` + `financials_{날짜}_{기업명}.json`
  - 섹션 3: `financials_{날짜}_{기업명}.json`
  - 섹션 4: `analysis_{날짜}_{기업명}.json` (industry 폴더)
  - 섹션 5: `analysis_{날짜}_{기업명}.json` (telegram 폴더) + `analysis_{날짜}_{기업명}.json` (news 폴더)
  - 섹션 6: `val_results_{날짜}_{기업명}.json` + `val_inputs_{날짜}_{기업명}.json`
  - 섹션 7: 모든 에이전트 데이터 교차 종합
- **즉시 저장**: 각 섹션 완성 직후 `report_{날짜}_{기업명}.md`에 Append

## 섹션별 작성 순서

```
[Step 3-1] 섹션 1: 기업 개요 및 데이터 커버리지
[Step 3-2] 섹션 2: 비즈니스모델 분석
[Step 3-3] 섹션 3: 재무 실적 분석
[Step 3-4] 섹션 4: 산업·시장 환경
[Step 3-5] 섹션 5: 증권사 리포트·뉴스 종합
[Step 3-6] 섹션 6: 밸류에이션 종합
[Step 4]   섹션 7: 투자 시나리오 및 주가 전망
[Step 5]   Executive Summary (역순 작성)
[Step 6]   자기 검증
```

## 핵심 원칙

1. **출처 명시**: 모든 수치에 에이전트 출처 표기 (← DART / ← Telegram / ← Valuation 등)
2. **충돌 병기**: 에이전트 간 수치 충돌 시 LLM 임의 조정 금지 — 양측 출처 분리 기술
3. **데이터 없음 처리**: 에이전트 산출물 누락 시 해당 소섹션에 "○○ 에이전트 데이터 없음" 명시
4. **투자 권유 금지**: `self_check_list.md` 금지 표현 목록 반드시 준수
5. **분량 우선순위**: 섹션 7(시나리오·주가 전망)을 핵심으로 가장 충실히 작성
