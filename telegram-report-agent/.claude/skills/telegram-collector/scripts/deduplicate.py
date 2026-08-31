"""
중복 제거 및 메타데이터 JSON 생성 스크립트.
raw_reports/ 내 파일의 MD5 해시를 계산하여 중복을 제거하고,
collection_meta_{날짜}_{기업명}.json을 output/ 에 생성한다.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def normalize_filename(date_str: str, channel: str, original: str) -> str:
    date_part = date_str.replace("-", "")[:8]
    channel_part = sanitize(channel)[:20]
    original_part = sanitize(original)
    return f"{date_part}_{channel_part}_{original_part}"


def load_pending_meta(raw_dir: Path) -> list[dict]:
    meta_file = raw_dir / "_pending_meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    return []


def collect_file_records(raw_dir: Path, pending_meta: list[dict]) -> list[dict]:
    meta_index = {r["filename"]: r for r in pending_meta}
    records = []

    for f in sorted(raw_dir.iterdir()):
        if f.name.startswith("_") or not f.is_file():
            continue
        meta = meta_index.get(f.name, {})
        records.append({
            "path": f,
            "filename": f.name,
            "channel": meta.get("channel", "unknown"),
            "message_date": meta.get("message_date", "19700101"),
            "type": meta.get("type", f.suffix.lstrip(".").lower() or "unknown"),
            "size": f.stat().st_size,
        })

    return records


def deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    hash_map: dict[str, dict] = {}
    removed = 0

    for r in records:
        h = md5(r["path"])
        r["hash"] = h
        if h in hash_map:
            existing = hash_map[h]
            if r["message_date"] < existing["message_date"]:
                existing["path"].unlink(missing_ok=True)
                hash_map[h] = r
            else:
                r["path"].unlink(missing_ok=True)
            removed += 1
        else:
            hash_map[h] = r

    return list(hash_map.values()), removed


def rename_files(records: list[dict], raw_dir: Path) -> list[dict]:
    updated = []
    for r in records:
        new_name = normalize_filename(r["message_date"], r["channel"], r["path"].name)
        new_path = raw_dir / new_name
        if r["path"] != new_path:
            r["path"].rename(new_path)
        r["filename"] = new_name
        r["path"] = new_path
        updated.append(r)
    return updated


def build_meta_json(
    company: str,
    date_str: str,
    records: list[dict],
    total_collected: int,
    removed_count: int,
) -> dict:
    by_channel: dict[str, int] = defaultdict(int)
    by_format: dict[str, int] = defaultdict(int)

    file_entries = []
    for r in records:
        by_channel[r["channel"]] += 1
        by_format[r["type"]] += 1
        file_entries.append({
            "filename": r["filename"],
            "channel": r["channel"],
            "message_date": r["message_date"],
            "hash": r.get("hash", ""),
            "extraction_status": "pending",
            "quality_flag": "normal",
        })

    today = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:8]

    return {
        "keyword": company,
        "collection_date": today,
        "period": {
            "from": "",  # collect_messages.py에서 채움
            "to": today,
        },
        "total_collected": total_collected,
        "after_dedup": len(records),
        "duplicates_removed": removed_count,
        "by_channel": dict(by_channel),
        "by_format": dict(by_format),
        "extraction_success": 0,  # extract_text.py 실행 후 갱신
        "files": file_entries,
    }


def main():
    parser = argparse.ArgumentParser(description="중복 제거 및 메타데이터 생성")
    parser.add_argument("--raw-dir", required=True, help="raw_reports 폴더 경로")
    parser.add_argument("--output-dir", required=True, help="output 폴더 경로")
    parser.add_argument("--company", required=True, help="기업명")
    parser.add_argument("--date", required=True, help="실행일 YYYYMMDD")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pending_meta = load_pending_meta(raw_dir)
    records = collect_file_records(raw_dir, pending_meta)
    total_collected = len(records)

    print(f"[deduplicate] 수집 파일 수: {total_collected}")

    if total_collected == 0:
        print("[deduplicate] ERROR: 수집된 파일이 없습니다. 에스컬레이션 필요.")
        raise SystemExit(1)

    records, removed = deduplicate(records)
    print(f"[deduplicate] 중복 제거: {removed}건 삭제, 잔존: {len(records)}건")

    if len(records) == 0:
        print("[deduplicate] ERROR: 중복 제거 후 0건. 수집 기간 확인 필요.")
        raise SystemExit(1)

    records = rename_files(records, raw_dir)

    meta = build_meta_json(args.company, args.date, records, total_collected, removed)
    meta_path = output_dir / f"collection_meta_{args.date}_{args.company}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[deduplicate] 메타데이터 저장: {meta_path}")

    # 임시 메타 파일 정리
    pending_file = raw_dir / "_pending_meta.json"
    if pending_file.exists():
        pending_file.unlink()


if __name__ == "__main__":
    main()
