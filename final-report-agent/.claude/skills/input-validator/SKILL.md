# input-validator 스킬

## 목적
5개 에이전트 산출물 파일 존재 여부를 검증하고, 출력 폴더를 생성하며, 모든 JSON 데이터를 에이전트별 파싱 로직으로 로딩·정규화한다.

## 스크립트 목록

| 스크립트 | 역할 |
|---------|------|
| `setup_and_validate.py` | 출력 폴더 생성 + 필수·선택 파일 존재 확인 + missing_inputs.log 기록 |
| `load_and_normalize.py` | 5개 에이전트 JSON 로딩, 단위 정규화(억원), 요약 딕셔너리 생성 |

## 실행 방법

### setup_and_validate.py
```bash
uv run setup_and_validate.py \
  --company {기업명} \
  --date {날짜} \
  --base-path C:/claude/stock/{기업명}/{날짜}
```

**출력:**
- `C:/claude/stock/{기업명}/{날짜}/final/` 폴더 생성
- `missing_inputs.log` 기록
- stdout에 JSON 결과 (can_proceed, present_files, missing_required, missing_optional)
- 필수 파일 누락 시 exit(1)

### load_and_normalize.py
```bash
uv run load_and_normalize.py \
  --company {기업명} \
  --date {날짜} \
  --base-path C:/claude/stock/{기업명}/{날짜} \
  --output-path C:/claude/stock/{기업명}/{날짜}/final/
```

**출력:** `normalized_summary.json` — 아래 구조

```json
{
  "company": "삼성전자",
  "analysis_date": "20260602",
  "current_price": 75000,
  "dart_summary": { ... },
  "telegram_summary": { ... },
  "news_summary": { ... },
  "industry_summary": { ... },
  "valuation_summary": { ... },
  "data_coverage": {
    "dart": true,
    "telegram": true,
    "news": false,
    "industry": true,
    "valuation": true
  }
}
```

## 주의사항
- 5개 에이전트는 독립 설계되어 JSON 키 이름·단위·구조가 다를 수 있음
- `load_and_normalize.py`는 에이전트별 파싱 로직을 분리 구현 (파싱 오류 시 스킵 + 로그)
- 단위는 모두 억원으로 통일 (조원 입력 시 × 10000 변환)
- 새 에이전트 출력 형식 변경 시 해당 파서 섹션 업데이트 필요
