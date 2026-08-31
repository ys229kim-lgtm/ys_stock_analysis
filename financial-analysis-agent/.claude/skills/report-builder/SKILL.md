# SKILL: report-builder

## 목적
LLM 분석 텍스트 + 차트 + 재무 데이터를 조합하여 최종 산출물을 생성한다.

## 사전 조건
```bash
pip install python-docx
npm install docx   # generate_report_docx.js가 있는 폴더에서 실행
```
Node.js 런타임 설치 필요.

## 실행 순서

### 1. 출력 폴더 확인
이미 생성된 경우 스킵.
```bash
python .claude/skills/report-builder/scripts/setup_output_dir.py \
  --date {YYYYMMDD} --company-name {기업명} \
  --base-dir C:/claude/stock/financial-analysis-agent
```

### 2. 분석 텍스트 저장
Step 5에서 작성한 분석 내용을 파일로 저장:
`{output_dir}/analysis_{date}_{company}.txt`

### 3. 마크다운 리포트 생성
```bash
python .claude/skills/report-builder/scripts/generate_md.py \
  --analysis {output_dir}/analysis_{date}_{company}.txt \
  --financials {output_dir}/financials_{date}_{company}.json \
  --charts-dir {output_dir}/charts/ \
  --output {output_dir}/report_{date}_{company}.md \
  --date "{분석일자}"
```

### 4. 재무 데이터 Word 생성
```bash
python .claude/skills/report-builder/scripts/generate_financials_docx.py \
  --financials {output_dir}/financials_{date}_{company}.json \
  --output {output_dir}/financials_{date}_{company}.docx \
  [--competitors {comp1.json} {comp2.json}]
```

### 5. 분석 리포트 Word 생성
```bash
node .claude/skills/report-builder/scripts/generate_report_docx.js \
  --analysis {output_dir}/analysis_{date}_{company}.txt \
  --financials {output_dir}/financials_{date}_{company}.json \
  --charts-dir {output_dir}/charts/ \
  --output {output_dir}/report_{date}_{company}.docx
```

### 6. 검증
```bash
python .claude/skills/report-builder/scripts/validate.py \
  {output_dir}/financials_{date}_{company}.docx \
  {output_dir}/report_{date}_{company}.docx
```

### 7. 완료 메시지 출력
```
=== 재무분석 리포트 생성 완료 ===
기업명: {기업명}
분석 기간: {start_year}–{end_year}
출력 폴더: {output_dir}/
  - financials_{date}_{company}.json
  - financials_{date}_{company}.docx
  - charts/ ({n}개 차트)
  - report_{date}_{company}.md
  - report_{date}_{company}.docx
```

## 실패 처리
- docx 생성 실패: md만 최종 산출, 오류 로그 + 사용자 안내
- financials.docx 실패: json만 유지, 스킵 + 로그 (리포트 계속)
