"""
출력 폴더 구조 생성 스크립트 (Step 0).
./{YYYYMMDD}_{기업명}_telegram/ 하위 raw_reports/, extracted_text/, output/ 생성.
"""
import argparse
import os
from pathlib import Path


SUBDIRS = ["raw_reports", "extracted_text", "output"]


def create_output_structure(base_dir: Path, company: str, date: str) -> Path:
    folder_name = f"{date}_{company}_telegram"
    root = base_dir / folder_name
    for sub in SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def main():
    parser = argparse.ArgumentParser(description="출력 폴더 구조 생성")
    parser.add_argument("--base-dir", default=".", help="생성 위치 (기본: 현재 디렉토리)")
    parser.add_argument("--company", required=True, help="기업명")
    parser.add_argument("--date", required=True, help="실행일 YYYYMMDD")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    root = create_output_structure(base_dir, args.company, args.date)

    print(f"[setup_dirs] 출력 폴더 생성 완료: {root}")
    for sub in SUBDIRS:
        path = root / sub
        status = "OK" if path.exists() else "FAIL"
        print(f"  [{status}] {path}")

    # 실패한 폴더가 있으면 종료 코드 1
    missing = [root / s for s in SUBDIRS if not (root / s).exists()]
    if missing:
        print("[setup_dirs] ERROR: 일부 폴더 생성 실패. 경로 권한을 확인하세요.")
        raise SystemExit(1)

    # 경로를 표준 출력으로 출력 (에이전트가 파싱하여 이후 단계에서 사용)
    print(f"\nOUTPUT_ROOT={root}")


if __name__ == "__main__":
    main()
