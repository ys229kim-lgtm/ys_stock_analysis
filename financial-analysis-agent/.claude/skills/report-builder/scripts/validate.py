#!/usr/bin/env python3
"""
validate.py — docx 파일 경량 검증 (존재 여부 + python-docx 로드 성공)

Usage:
    python validate.py financials.docx report.docx
"""

import sys
from pathlib import Path


def validate(filepath: str) -> bool:
    p = Path(filepath)
    if not p.exists():
        print(f"[FAIL] 파일 없음: {filepath}")
        return False
    try:
        from docx import Document
        Document(str(p))
        size_kb = p.stat().st_size / 1024
        print(f"[OK]   {p.name} ({size_kb:.1f} KB)")
        return True
    except Exception as e:
        print(f"[FAIL] {p.name} — 로드 오류: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py <file1.docx> [file2.docx ...]")
        sys.exit(1)
    results = [validate(f) for f in sys.argv[1:]]
    ok = sum(results)
    print(f"\n검증 결과: {ok}/{len(results)} 정상")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
