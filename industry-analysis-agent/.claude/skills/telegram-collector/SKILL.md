# 텔레그램 수집 스킬 (telegram-collector)

## 목적
산업명 기반 키워드로 텔레그램 채널에서 산업 리포트를 검색·다운로드·텍스트 추출한다.

## 트리거
Step 0 완료 직후 (Step 3과 병렬 시작)

## 수행 절차

### 1. 키워드 자동 생성 (LLM)

산업명과 선택된 세그먼트를 기반으로 LLM이 런타임에 생성:

```
기본 키워드 (항상 포함):
  - {산업명}
  - {산업명} 리포트
  - {산업명} 산업분석
  - {산업명} 전망 {현재연도}
  - {industry_en} outlook {현재연도}

세그먼트 키워드 (LLM 자동 도출 3~5개):
  예시(반도체/HBM): HBM, DRAM, 파운드리, 메모리반도체, NAND
  예시(2차전지/양극재): 양극재, NCA, NCM, 리튬, 전구체
```

### 2. 텔레그램 검색

각 키워드에 대해 `mcp__telegram-mcp__search_messages` 호출:
- limit: 50 (키워드당)
- 대상: 구독 채널 전체
- 수집 기간: 최근 1년

첨부 파일 있는 메시지 우선 처리. `mcp__telegram-mcp__download_media`로 다운로드.

저장 경로: `{출력폴더}/raw_reports/{YYYYMMDD}_{채널명}_{파일명}`

### 3. 수집 결과 판단

| 결과 | 처리 |
|------|------|
| 0건 | 로그 기록 후 Step 3 결과만으로 진행, 리포트에 "텔레그램 데이터 부재" 명시 |
| 1~4건 | 채널 구독 권장 메시지 출력 후 계속 진행 |
| 5건 이상 | 정상 진행 |
| MCP 오류 | 재시도 3회 → 스킵 |

### 4. 채널 구독 권장 메시지 형식

```
⚠️ 텔레그램 산업 리포트가 {N}건으로 충분하지 않습니다.
'{산업명}' 관련 다음 채널 구독을 권장합니다:
- [LLM이 산업별 관련 채널 목록 제안]
계속 진행하시겠습니까? (예/아니오)
```

### 5. 텍스트 추출 (Step 2)

스크립트: `scripts/extract_and_filter.py`

처리 순서:
1. PDF → `pdfplumber` 텍스트 추출
2. PDF 실패 → `pytesseract` OCR
3. 이미지(JPG/PNG) → `pytesseract` OCR
4. 파일 MD5 해시로 중복 제거
5. 관련성 필터: 파일명 + 추출 텍스트 첫 500자에 산업명 키워드 포함 여부
   - 포함 → `extracted_text/` 저장
   - 미포함 → `irrelevant: true` 태그, 분석 제외
6. `collection_meta_{날짜}_{기업명}.json` 생성

## 의존성
```
pdfplumber>=0.10.0
pytesseract>=0.3.10
Pillow>=10.0.0
```

## 스크립트
- `scripts/collect_reports.py` — MCP 호출 + 다운로드 자동화
- `scripts/extract_and_filter.py` — 텍스트 추출 + 관련성 필터
