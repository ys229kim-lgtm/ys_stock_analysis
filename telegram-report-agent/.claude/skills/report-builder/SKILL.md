# Skill: report-builder

## 목적

출력 폴더 구조 생성(Step 0)과 분석 결과를 마크다운(.md) 및 Word(.docx) 문서로 생성(Step 6)한다.

## 트리거 조건

- **Step 0**: 워크플로우 최초 시작 시 (`setup_dirs.py`)
- **Step 6**: Step 5 (LLM 종합 분석) 완료 직후 (`generate_md.py`, `generate_docx.py`)

---

## 스크립트 목록

| 스크립트 | 실행 단계 | 역할 |
|----------|----------|------|
| `setup_dirs.py` | Step 0 | 출력 폴더 구조 생성 |
| `generate_md.py` | Step 6 | 마크다운 리포트 생성 |
| `generate_docx.py` | Step 6 | Word 문서 생성 |

---

## Step 0: 폴더 생성

```bash
python setup_dirs.py --base-dir C:/claude/stock/telegram-report-agent --company {기업명} --date {YYYYMMDD}
```

생성 구조:
```
C:/claude/stock/telegram-report-agent/{YYYYMMDD}_{기업명}_telegram/
  ├── raw_reports/
  ├── extracted_text/
  └── output/
```

성공 기준: 3개 폴더 모두 생성 확인
실패 처리: 권한 오류 시 에스컬레이션

---

## Step 6: 문서 생성

### 마크다운 생성

```bash
python generate_md.py \
  --analysis-json {analysis JSON 경로} \
  --synthesis-text {종합 분석 텍스트 파일 경로} \
  --output-dir {output 경로} \
  --company {기업명} \
  --date {YYYYMMDD}
```

### Word 문서 생성

```bash
python generate_docx.py \
  --md-file {생성된 md 파일 경로} \
  --analysis-json {analysis JSON 경로} \
  --output-dir {output 경로} \
  --company {기업명} \
  --date {YYYYMMDD}
```

---

## 문서 구조 (md / docx 공통)

```
표지: 기업명, 분석일자, 수집 리포트 수, 수집 기간
목차
1. 수집 개요 (채널별/형식별 분포 테이블)
2. 투자의견 분포 (Buy/Hold/Sell 테이블 + 목표주가 범위)
3. 긍정 논거 통합 (빈도순, 출처 증권사 명시)
4. 부정 논거 통합 (빈도순, 출처 증권사 명시)
5. 실적 전망 컨센서스 (추정치 범위 테이블)
6. Best Case 시나리오 [전제조건 / 목표주가 / 기대실적]
7. Worst Case 시나리오 [전제조건 / 예상주가 / 예상실적]
8. 종합 시각 요약
부록: 리포트별 분석 상세 (증권사 / 날짜 / 의견 / 목표주가 테이블)
```

---

## 의존성

```
python-docx>=1.1
```

---

## 성공 기준 / 실패 처리

- md + docx 두 파일 모두 생성 확인
- docx 생성 실패 시: md만 저장, 오류 로그 기록 후 완료 처리 (전체 중단 금지)
