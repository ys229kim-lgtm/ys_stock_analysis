# Skill: report-analyzer

## 목적

에이전트(LLM)가 직접 수행하는 분석 단계의 지침을 제공한다. 참조 문서를 통해 리포트별 구조화 추출(Step 4)과 종합 교차 분석(Step 5)을 수행한다.

## 트리거 조건

Step 3 (text-extractor) 완료 직후. `extracted_text/` 폴더에 `.txt` 파일이 존재해야 한다.

---

## 참조 문서

| 문서 | 용도 |
|------|------|
| `references/extraction_schema.md` | Step 4: 리포트별 추출 항목 스키마 및 판단 지침 |
| `references/analysis_framework.md` | Step 5: 종합 분석 8개 섹션 프레임워크 |

---

## Step 4: 리포트별 구조화 분석

**처리 단위:** `extracted_text/` 내 `.txt` 파일 1개 = 리포트 1건

**처리 방식:**
1. 각 txt 파일을 순서대로 읽는다.
2. `extraction_schema.md`에 정의된 JSON 구조로 분석한다.
3. 분석 결과를 `output/analysis_{날짜}_{기업명}.json`의 `reports` 배열에 누적 저장한다.
4. 30건 초과 시 JSON 파일을 저장하고 재로드하여 컨텍스트 윈도우 초과를 방지한다.

**자기 검증 (각 리포트 완료 후):**
- [ ] `source_file`, `report_date`, `bullish_points`, `bearish_points` 존재
- [ ] `investment_opinion` 존재 (null 불허)
- [ ] 수치 필드에 문자열 혼입 없음
- 실패 시 해당 리포트 재분석 1회, 2회 실패 시 `parse_failed: true` 기록 후 스킵

---

## Step 5: 종합 분석

**입력:** `output/analysis_{날짜}_{기업명}.json` 전체 로드

**출력:** `analysis_framework.md`의 8개 섹션 구조로 서술

**자기 검증 (종합 분석 완료 후):**
- [ ] 8개 섹션 모두 서술 존재
- [ ] Best/Worst Case에 전제조건 + 주가범위 + 실적범위 포함
- [ ] 수치 인용 시 출처(날짜 + 증권사) 명시
- [ ] 근거 없는 전망 없음
- 실패 시 해당 섹션 재작성 최대 1회
- 유효 리포트 수 < 3건 → 섹션 첫머리에 신뢰도 낮음 경고 삽입
