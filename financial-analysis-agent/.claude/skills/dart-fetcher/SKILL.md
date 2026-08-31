# SKILL: dart-fetcher

## 목적
dart-mcp MCP 도구로 대상 기업의 재무제표 10개년치를 수집하고 정규화 JSON으로 저장한다.

## 실행 절차

### 1. 오늘 날짜 확인
`mcp__dart-mcp__get_current_date` 호출 → date_str(YYYYMMDD) 설정.

### 2. 연결재무제표 수집
`mcp__dart-mcp__search_detailed_financial_data` 호출:
- corp_code: 입력 종목코드
- start_date: 11년 전 YYYYMMDD
- end_date: 오늘 + 95일 YYYYMMDD (공시 지연 반영)
- report_type: 사업보고서

XBRL 실패 시 → `mcp__dart-mcp__search_json_financial_data` 로 폴백.

### 3. 연결 기준 없으면 별도 기준 재시도
별도 사용 시 company.report_type = "별도" 설정.

### 4. 세그먼트 수집 (선택)
`mcp__dart-mcp__search_business_information` 으로 세그먼트 요청.
실패 → 로그 후 스킵 (수익구조 섹션 자동 생략).

### 5. 수집 데이터 저장
MCP 응답을 JSON 파일로 저장한 후 fetch_dart.py 실행:

```bash
python .claude/skills/dart-fetcher/scripts/fetch_dart.py \
  --from-mcp-output <저장한_mcp_response.json 경로> \
  --corp-code {종목코드} \
  --company-name {기업명} \
  --output-dir ./{date_str}_{기업명}/
```

## 오류 처리
- API 오류: 최대 3회 재시도 (30초 간격)
- 3회 실패: 사용자에게 종목코드 확인 요청 후 중단
- 현금흐름표 없음: 경고 로그 후 나머지 진행
- 5개년 미만: 경고 로그 후 진행

## 출력
`{output_dir}/dart_normalized_{date}_{company}.json`
