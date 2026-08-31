#!/usr/bin/env python3
"""
setup_output_dir.py — 출력 폴더 및 하위 charts/ 폴더 생성

Usage:
    python setup_output_dir.py --date 20260602 --company-name 삼성전자
    # 생성된 폴더 절대 경로를 stdout에 출력
"""

import argparse
from pathlib import Path
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",         default=None, help="YYYYMMDD (생략 시 오늘)")
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--base-dir",     default=".")
    args = parser.parse_args()

    date_str    = args.date or datetime.now().strftime("%Y%m%d")
    folder_name = f"{date_str}_{args.company_name}"
    folder      = Path(args.base_dir) / folder_name

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "charts").mkdir(exist_ok=True)

    print(str(folder.resolve()))


if __name__ == "__main__":
    main()
