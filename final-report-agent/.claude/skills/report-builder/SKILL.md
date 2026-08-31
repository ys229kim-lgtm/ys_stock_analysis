# report-builder 스킬

## 목적
최종 리포트 산출물(통합 JSON + Markdown + Word)을 생성한다.

## 스크립트 목록

| 스크립트 | 역할 |
|---------|------|
| `generate_integrated_json.py` | normalized_summary + 시나리오 결과 → integrated JSON |
| `generate_md.py` | 섹션 파일들 병합 → 최종 Markdown 리포트 |
| `generate_docx.py` | Markdown → Word(.docx) 변환 (python-docx) |

## 실행 방법

```bash
# 통합 JSON
uv run generate_integrated_json.py \
  --company {기업명} --date {날짜} \
  --final-path C:/claude/stock/{기업명}/{날짜}/final/

# Markdown (섹션 파일 병합)
uv run generate_md.py \
  --company {기업명} --date {날짜} \
  --final-path C:/claude/stock/{기업명}/{날짜}/final/

# Word 문서 (python-docx)
uv run generate_docx.py \
  --company {기업명} --date {날짜} \
  --final-path C:/claude/stock/{기업명}/{날짜}/final/
```

## Word 문서 스타일 규칙

- **제목(H1)**: 18pt Bold, 진한 파란색 (#1F3864)
- **섹션(H2)**: 14pt Bold, 중간 파란색 (#2F5496)
- **소섹션(H3)**: 12pt Bold, 검정
- **표**: 헤더 배경 진한 파란색·흰색 글씨; 행 번갈아 흰색/연한 회색 (#F2F2F2)
- **강조**: 밸류에이션 테이블 upside% — 양수 녹색, 음수 빨강
- **페이지 여백**: 상하좌우 25mm
- **표지**: 기업명·분석일자·현재주가·가중평균 적정가·upside%

## 섹션 파일 병합 규칙 (generate_md.py)

에이전트가 섹션 완성 즉시 Append 저장한 `report_{날짜}_{기업명}.md`를 기반으로:
1. 표지 삽입
2. Executive Summary 삽입
3. 목차 자동 생성
4. 섹션 1~7 본문
5. 부록 A·B·C

## 실패 처리

| 상황 | 처리 |
|------|------|
| md 생성 실패 | 에이전트가 직접 md 내용 재작성 후 저장 |
| docx 생성 실패 | md + JSON만 저장, error_log.txt 기록, 완료 처리 |
| python-docx 미설치 | "pip install python-docx 필요" 안내 후 md로 완료 |

## 의존성

```
python-docx >= 1.1
```

설치:
```bash
pip install python-docx
```
