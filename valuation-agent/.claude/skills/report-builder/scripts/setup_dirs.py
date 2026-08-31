"""
밸류에이션 에이전트 출력 폴더 생성.
다른 에이전트들(financial, telegram, industry)의 같은 구조와 통일.
"""

import argparse
import os
from pathlib import Path
from datetime import date


def setup_dirs(output_base: str) -> dict:
    base = Path(output_base)
    base.mkdir(parents=True, exist_ok=True)

    created = [str(base)]
    print(f"[OK] 출력 폴더 생성: {base}")
    return {"base": str(base), "created": created}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-base", required=True,
                        help="예: C:/claude/stock/삼성전자/20260602/valuation")
    args = parser.parse_args()

    result = setup_dirs(args.output_base)
    print(f"[OK] 폴더 준비 완료: {result['base']}")


if __name__ == "__main__":
    main()
