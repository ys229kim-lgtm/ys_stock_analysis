# Telegram MCP 사용 가이드

## 연결 확인

작업 시작 전 `mcp__telegram-mcp__get_me`로 계정 접속 상태를 확인한다.

```
get_me() → { id, username, first_name }
```

---

## 메시지 검색

### search_messages

키워드로 접속 계정이 구독 중인 전체 채널/그룹/DM에서 메시지를 검색한다.

**주요 파라미터:**
- `query` (str): 검색 키워드
- `limit` (int): 반환 최대 건수 (기본 20, 최대 100)
- `offset_date` (int, optional): 이 Unix timestamp 이전 메시지만 검색

**날짜 필터 적용법:**
- Telegram MCP는 직접적인 `from_date` 파라미터를 제공하지 않을 수 있다.
- 반환된 메시지의 `date` 필드(Unix timestamp)를 확인하여 365일 이전 메시지는 수집에서 제외한다.

**반환 구조 (예시):**
```json
[
  {
    "id": 12345,
    "date": 1704067200,
    "chat_id": -100123456789,
    "chat_title": "증권리포트채널",
    "text": "삼성전자 목표주가 상향...",
    "media": {
      "type": "document",
      "file_id": "BQACAgIAA...",
      "file_name": "samsung_report_2024.pdf",
      "file_size": 1234567
    }
  }
]
```

**반복 호출 전략:**
- 한 번에 최대 100건 반환 → `offset_date`를 마지막 메시지 날짜로 설정하여 페이징
- 365일 이전 메시지가 나오면 수집 종료

---

## 파일 다운로드

### download_media

메시지에 첨부된 파일을 로컬에 저장한다.

**주요 파라미터:**
- `chat_id` (int | str): 채널/그룹 ID
- `message_id` (int): 메시지 ID
- `file_path` (str): 저장할 로컬 경로 (raw_reports/ 하위 경로 지정)

**사용 예시:**
```
download_media(
  chat_id=-100123456789,
  message_id=12345,
  file_path="./20260604_삼성전자_telegram/raw_reports/samsung_report.pdf"
)
```

**실패 처리:**
- 다운로드 실패 시 최대 2회 재시도
- 2회 실패 시 `extraction_status: "failed"` 기록 후 스킵

---

## 채널 목록 확인

### get_chats / list_chats

접속 계정이 현재 구독 중인 채널/그룹 목록을 반환한다. 검색 전 어떤 채널에서 리포트를 수집할 수 있는지 확인할 때 사용.

---

## 레이트 리밋 대응

- Telegram API는 분당 20~30건 내외 요청을 권장
- 다운로드 루프에서 각 요청 사이 **1초 대기** 적용
- 429 (FloodWait) 오류 수신 시 `retry_after` 초만큼 대기 후 재시도

---

## 제약사항

- **구독 채널만 검색 가능**: 미구독 비공개 채널은 검색 불가 → 스킵 후 로그 기록
- **개인 계정 기준**: 봇 토큰이 아닌 사용자 계정으로 접속
- **대용량 파일**: 파일 크기 > 20MB 는 다운로드 실패 가능 → 메타데이터만 기록
