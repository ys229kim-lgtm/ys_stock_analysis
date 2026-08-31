"""
Step 0: 출력 폴더 구조 생성
Usage: python setup_dirs.py --company 삼성전자 --date 20260608
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("C:/claude/stock/industry-analysis-agent")


def create_output_dirs(company: str, date: str) -> Path:
    folder_name = f"{date}_{company}_industry"
    output_root = BASE_DIR / folder_name

    dirs = [
        output_root / "raw_reports",
        output_root / "extracted_text",
        output_root / "output",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    meta = {
        "company": company,
        "created_at": datetime.now().isoformat(),
        "output_root": str(output_root),
        "dirs": [str(d) for d in dirs],
    }

    meta_path = output_root / "output" / f"setup_meta_{date}_{company}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[setup_dirs] 출력 폴더 생성 완료: {output_root}")
    print(f"  - raw_reports/")
    print(f"  - extracted_text/")
    print(f"  - output/")
    return output_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True, help="기업명")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="날짜 (YYYYMMDD)")
    args = parser.parse_args()

    root = create_output_dirs(args.company, args.date)
    print(json.dumps({"output_root": str(root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
