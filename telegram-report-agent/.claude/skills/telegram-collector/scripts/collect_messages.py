"""
텔레그램 메시지 검색 및 수집 스크립트.
이 스크립트는 Claude Code 에이전트가 Telegram MCP를 호출하기 전
수집 파라미터를 준비하고 다운로드된 파일을 정리하는 역할을 한다.
실제 MCP 호출은 에이전트가 직접 수행한다.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


RATE_LIMIT_DELAY = 1.0  # 요청 간 대기 초 (레이트 리밋 방지)
MAX_RETRY = 2


def build_date_range(period_days: int = 365) -> tuple[str, str]:
    end = datetime.today()
    start = end - timedelta(days=period_days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def build_collection_params(company: str, stock_code: str | None, period_days: int = 365) -> dict:
    date_from, date_to = build_date_range(period_days)
    keywords = [company]
    if stock_code:
        keywords.append(stock_code)

    return {
        "keywords": keywords,
        "date_from": date_from,
        "date_to": date_to,
        "period_days": period_days,
        "rate_limit_delay": RATE_LIMIT_DELAY,
        "max_retry": MAX_RETRY,
    }


def save_text_message(text: str, channel: str, date_str: str, index: int, raw_dir: Path) -> dict:
    filename = f"{date_str}_{sanitize_filename(channel)}_text_{index:04d}.txt"
    filepath = raw_dir / filename
    filepath.write_text(text, encoding="utf-8")
    return {
        "filename": filename,
        "channel": channel,
        "message_date": date_str,
        "type": "text",
        "size": len(text.encode("utf-8")),
    }


def load_existing_meta(raw_dir: Path) -> list[dict]:
    meta_file = raw_dir / "_pending_meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    return []


def save_pending_meta(raw_dir: Path, records: list[dict]) -> None:
    meta_file = raw_dir / "_pending_meta.json"
    meta_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="수집 파라미터 준비 및 텍스트 메시지 저장")
    parser.add_argument("--company", required=True, help="기업명")
    parser.add_argument("--stock-code", default=None, help="종목코드 (선택)")
    parser.add_argument("--raw-dir", required=True, help="raw_reports 폴더 경로")
    parser.add_argument("--period-days", type=int, default=365, help="수집 기간(일)")
    parser.add_argument("--print-params", action="store_true", help="수집 파라미터를 JSON으로 출력")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    params = build_collection_params(args.company, args.stock_code, args.period_days)

    if args.print_params:
        print(json.dumps(params, ensure_ascii=False, indent=2))
        return

    print(f"[collect_messages] 수집 파라미터 준비 완료")
    print(f"  키워드: {params['keywords']}")
    print(f"  기간: {params['date_from']} ~ {params['date_to']}")
    print(f"  저장 경로: {raw_dir}")


if __name__ == "__main__":
    main()
