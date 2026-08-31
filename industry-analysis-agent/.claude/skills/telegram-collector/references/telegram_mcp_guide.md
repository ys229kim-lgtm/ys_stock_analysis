# 텔레그램 MCP 사용 가이드

## 핵심 도구

| 도구 | 용도 |
|------|------|
| `mcp__telegram-mcp__search_messages` | 키워드로 메시지 검색 |
| `mcp__telegram-mcp__download_media` | 첨부 파일 다운로드 |
| `mcp__telegram-mcp__get_history` | 특정 채널 최근 메시지 조회 |
| `mcp__telegram-mcp__list_chats` | 구독 채널 목록 조회 |

## search_messages 호출 예시

```json
{
  "query": "반도체 산업분석",
  "limit": 50
}
```

반환 필드에서 확인:
- `message.id`: 메시지 ID
- `message.chat.id`: 채널 ID
- `message.media`: 첨부 파일 존재 여부
- `message.document.file_name`: 파일명
- `message.date`: 메시지 날짜

## download_media 호출 예시

```json
{
  "chat_id": -1001234567890,
  "message_id": 12345,
  "file_path": "C:/claude/stock/industry-analysis-agent/20260608_삼성전자_industry/raw_reports/20260608_채널명_파일명.pdf"
}
```

## 수집 전략

### 키워드 순서
1. 산업명 단독 (가장 넓은 검색)
2. 산업명 + 리포트
3. 산업명 + 전망
4. 세그먼트 키워드들 (LLM 생성)

### 날짜 필터링
- 반환된 message.date를 확인하여 1년 이내 메시지만 처리
- 날짜 형식: Unix timestamp (datetime.fromtimestamp()으로 변환)

### 파일 형식별 처리
| 확장자 | 처리 방법 |
|--------|---------|
| .pdf | pdfplumber → pytesseract 순 |
| .jpg, .png | pytesseract OCR |
| .txt, .md | 직접 읽기 |
| 기타 | 메타데이터만 수집 |

## 채널 구독 권장 메시지 (저조 시)

산업별 관련 채널 예시 목록 (LLM이 최신 상태로 업데이트):

**반도체:**
- 반도체 관련 증권사 리서치 채널
- 글로벌 반도체 뉴스 채널

**2차전지:**
- 배터리·전기차 산업 분석 채널

**바이오·제약:**
- 제약·바이오 리포트 채널

> 실제 채널명은 LLM이 현재 시점 기준으로 제안한다.
