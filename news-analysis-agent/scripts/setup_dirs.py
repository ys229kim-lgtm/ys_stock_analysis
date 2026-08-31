"""출력 폴더 생성 스크립트."""

import argparse
import sys
from pathlib import Path


def setup_dirs(output_base: str) -> None:
    base = Path(output_base)
    subdirs = ["raw", "fetched", "output"]

    for subdir in subdirs:
        target = base / subdir
        target.mkdir(parents=True, exist_ok=True)
        print(f"[OK] {target}")

    print(f"\n출력 폴더 생성 완료: {base}")


def main():
    parser = argparse.ArgumentParser(description="뉴스 분석 에이전트 출력 폴더 생성")
    parser.add_argument("--output-base", required=True, help="출력 기본 폴더 경로")
    args = parser.parse_args()

    try:
        setup_dirs(args.output_base)
    except PermissionError as e:
        print(f"[ERROR] 권한 오류: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
