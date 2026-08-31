# report-builder 스킬

## 목적
밸류에이션 분석 산출물을 구조화된 Markdown + Word(.docx) 리포트로 변환한다.

## 스크립트 목록

| 스크립트 | 역할 |
|---------|------|
| `setup_dirs.py` | 출력 폴더 구조 생성 |
| `generate_md.py` | val_results + disclosures + biz_model JSON → Markdown |
| `generate_docx.js` | Markdown → Word(.docx) 변환 (node.js, docx 패키지) |
| `generate_report.py` | generate_md.py + generate_docx.js 순차 실행 래퍼 |

## 폴더 구조

```bash
uv run setup_dirs.py --output-base {base_path}valuation
```

생성 폴더:
```
{base_path}valuation/
  └── (평면 구조, 서브폴더 없음)
```

## 리포트 섹션 구조

```
# {기업명} 밸류에이션 분석 리포트
## 작성일: {날짜} | 분석 기준: {base_date}

---
## 1. 비즈니스모델 분석
### 1-1. Price (가격 결정력)
### 1-2. Quantity (수요량)
### 1-3. Cost (비용 구조)
### 1-4. 강점 / 약점
### 1-5. 경제적 해자 (Moat)

---
## 2. 밸류에이션 종합
### 2-A. 5종 적정가 비교
| 방법 | 하단 | 중간 | 상단 | 현재가 대비 |
### 2-B. 증권사 콘센서스 vs. LLM 추정
### 2-C. 업종 태그 및 가중치 근거
### 2-D. 가중 평균 적정가
### 2-E. 종합 평가 (현재 주가 위치)
### 2-F. 방법 간 괴리 분석

---
## 3. 공시 이벤트
### 3-1. 주요 공시 (HIGH 중요도)
### 3-2. 진행 중 이슈
### 3-3. 향후 일정

---
## 4. 종합 투자 관점 요약

---
## 부록: 가정 및 입력값
### A. WACC 계산
### B. 밸류에이션 입력값 상세
### C. 데이터 소스
```

## Word 문서 스타일 규칙

- **제목(H1)**: 18pt Bold, 진한 파란색 (#1F3864)
- **섹션(H2)**: 14pt Bold, 중간 파란색 (#2F5496)
- **소섹션(H3)**: 12pt Bold, 검정
- **표**: 헤더 배경 진한 파란색, 흰색 글씨; 행 번갈아 흰색/연한 회색
- **강조**: 적정가 테이블에서 "현재가 대비 %" 컬럼 — 양수 녹색, 음수 빨강
- **페이지 여백**: 상하좌우 25mm

## 실행 방법

```bash
# generate_report.py가 모든 것 처리
uv run generate_report.py \
  --analysis-dir {base_path}valuation/ \
  --company {기업명} \
  --date {날짜}
```

내부 실행 순서:
1. `python generate_md.py` → `report_{날짜}_{기업명}.md` 생성
2. `node generate_docx.js report_{날짜}_{기업명}.md report_{날짜}_{기업명}.docx`

## 실패 처리

| 상황 | 처리 |
|------|------|
| md 생성 실패 | 에이전트가 직접 md 작성 후 docx 시도 |
| docx 생성 실패 | md만 저장, 오류 로그 기록, 완료 처리 |
| node 미설치 | "node.js 미설치로 docx 생성 불가" 경고 후 md로 완료 |
