"""
Step 1: 텔레그램 MCP 호출 가이드 스크립트
이 스크립트는 Claude Code 에이전트가 MCP 도구를 직접 호출하는 순서를 안내한다.
실제 MCP 호출은 에이전트가 mcp__telegram-mcp__* 도구로 수행한다.
"""

COLLECTION_GUIDE = """
=== 텔레그램 산업 리포트 수집 절차 ===

1. 키워드 목록 준비 (LLM이 생성)
   - 산업명, 산업명+리포트, 산업명+전망, 세그먼트 키워드 3~5개

2. 각 키워드에 대해 mcp__telegram-mcp__search_messages 호출:
   {
     "query": "{키워드}",
     "limit": 50
   }

3. 첨부 파일이 있는 메시지 필터링
   - message.media 또는 message.document 존재 여부 확인

4. mcp__telegram-mcp__download_media 호출:
   {
     "chat_id": "{채널 ID}",
     "message_id": "{메시지 ID}",
     "file_path": "{출력폴더}/raw_reports/{날짜}_{채널명}_{파일명}"
   }

5. 수집 결과 판단:
   - 0건: 로그 기록, Step 3 결과만으로 진행
   - 5건 미만: 채널 구독 권장 메시지 출력
   - 다운로드 실패 단건: 재시도 2회 → 메타데이터만 기록

6. extract_and_filter.py 실행:
   python extract_and_filter.py \\
     --raw_dir {출력폴더}/raw_reports \\
     --out_dir {출력폴더}/extracted_text \\
     --meta_path {출력폴더}/output/collection_meta_{날짜}_{기업명}.json \\
     --keywords {산업명} {세그먼트1} {세그먼트2} \\
     --company {기업명} --date {날짜}
"""

if __name__ == "__main__":
    print(COLLECTION_GUIDE)
