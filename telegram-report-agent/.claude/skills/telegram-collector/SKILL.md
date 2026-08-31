# Skill: telegram-collector

## 목적

Telegram MCP를 사용하여 기업명/종목코드 키워드로 메시지를 검색하고, 첨부파일(PDF·이미지)과 텍스트 메시지를 수집한다. 이후 `deduplicate.py`로 중복 제거 및 메타데이터 JSON을 생성한다.

## 트리거 조건

워크플로우 Step 1 시작 시 호출. 출력 폴더(raw_reports/)가 생성된 후 실행.

---

## Step 1: 메시지 검색 및 수집

### 사용 MCP 도구

- `mcp__telegram-mcp__search_messages` — 키워드로 메시지 검색
- `mcp__telegram-mcp__download_media` — 첨부파일 다운로드
- `mcp__telegram-mcp__get_chats` — 접속 계정의 채널/그룹 목록 확인

### 검색 절차

1. `search_messages`로 기업명 키워드 검색 (날짜 필터: 오늘 - 365일 이전)
2. 종목코드가 있으면 동일하게 별도 검색 후 결과 합산
3. 검색 결과 전체를 먼저 수집하여 PDF/이미지 첨부파일 목록을 파악한다
4. **PDF/이미지 전량 다운로드 (필수, 건너뛰기 금지)**:
   - 발견된 모든 PDF·이미지를 `download_media`로 `raw_reports/`에 저장
   - "텍스트로 충분하다"는 판단으로 다운로드 생략 불가
   - 다운로드 실패 시 2회 재시도 → 실패 시 `failed_downloads` 목록 기록 후 다음 파일 진행
5. 텍스트 전용 메시지 → `raw_reports/{날짜}_text_{index}.txt`로 저장
6. 전체 다운로드 완료 후 `raw_reports/` 파일 수·총 용량 로그 기록
7. 메타데이터 기록: 채널명, 메시지ID, 날짜, 파일명, 파일크기, 다운로드 성공/실패

### 분기 조건

```
수집 결과 = 0건?
  ├─ YES → 에스컬레이션 (사용자에게 키워드/구독 채널 확인 요청)
  └─ NO  → PDF 전량 다운로드 → Step 2 (deduplicate.py) 진행

첨부파일 다운로드 실패?
  ├─ 재시도 2회
  └─ 2회 실패 → failed_downloads 기록 후 다음 파일 계속 다운로드
               (전체 중단 금지 — 나머지 파일은 계속 받는다)
```

### 실패 처리

- telegram-mcp 연결 오류 → 60초 간격으로 자동 재시도 3회 → 에스컬레이션
- 레이트 리밋 감지(429 응답) → `deduplicate.py`의 rate_limit_delay 설정 참조

---

## Step 2: 중복 제거 및 메타데이터 생성

### 스크립트

```
.claude/skills/telegram-collector/scripts/deduplicate.py
```

### 실행 방법

```bash
python deduplicate.py --raw-dir {raw_reports 경로} --output-dir {output 경로} --company {기업명} --date {YYYYMMDD}
```

### 처리 내용

1. `raw_reports/` 내 모든 파일의 MD5 해시 계산
2. 동일 해시 파일 중 가장 오래된 날짜 기준 1개만 유지, 나머지 삭제
3. 파일명 정규화: `{날짜}_{채널명}_{원본파일명}` 형식으로 rename
4. `output/collection_meta_{날짜}_{기업명}.json` 생성

### 성공 기준

- `collection_meta` JSON 파일 생성 완료
- 중복 제거 후 최소 1건 잔존

### 실패 처리

- 중복 제거 후 0건 → 에스컬레이션 (수집 기간 조정 요청)
