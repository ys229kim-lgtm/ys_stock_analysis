"""
Step 2: 텔레그램 수집 파일 텍스트 추출 + 관련성 필터링
Usage: python extract_and_filter.py --raw_dir ./raw_reports --out_dir ./extracted_text
       --meta_path ./output/collection_meta.json --keywords 반도체 HBM DRAM
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def extract_text_from_pdf(path: Path) -> str:
    """pdfplumber 우선, 실패 시 pytesseract OCR."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
    except Exception:
        pass

    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(str(path))
        return "\n".join(pytesseract.image_to_string(img, lang="kor+eng") for img in images)
    except Exception as e:
        return f"[추출 실패: {e}]"


def extract_text_from_image(path: Path) -> str:
    """pytesseract OCR."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(path)
        return pytesseract.image_to_string(img, lang="kor+eng")
    except Exception as e:
        return f"[OCR 실패: {e}]"


def is_relevant(filename: str, text_snippet: str, keywords: list[str]) -> bool:
    """파일명 + 텍스트 첫 500자에 키워드 포함 여부."""
    combined = (filename + " " + text_snippet[:500]).lower()
    return any(kw.lower() in combined for kw in keywords)


def process_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix in (".jpg", ".jpeg", ".png", ".bmp", ".tiff"):
        return extract_text_from_image(path)
    elif suffix in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"[읽기 실패: {e}]"
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--meta_path", required=True)
    parser.add_argument("--keywords", nargs="+", default=[], help="관련성 판단 키워드 목록")
    parser.add_argument("--company", default="")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes: set[str] = set()
    results = []
    total = 0
    valid = 0
    duplicates = 0
    irrelevant = 0

    for fpath in sorted(raw_dir.iterdir()):
        if not fpath.is_file():
            continue
        total += 1

        # 중복 제거
        file_hash = md5_of_file(fpath)
        if file_hash in seen_hashes:
            duplicates += 1
            results.append({"file": fpath.name, "status": "duplicate", "hash": file_hash})
            continue
        seen_hashes.add(file_hash)

        # 텍스트 추출
        text = process_file(fpath)

        # 관련성 필터
        if args.keywords and not is_relevant(fpath.name, text, args.keywords):
            irrelevant += 1
            results.append({"file": fpath.name, "status": "irrelevant", "hash": file_hash})
            continue

        # 유효 파일 저장
        valid += 1
        out_path = out_dir / (fpath.stem + "_extracted.txt")
        out_path.write_text(text, encoding="utf-8")
        results.append({
            "file": fpath.name,
            "status": "valid",
            "hash": file_hash,
            "extracted_path": str(out_path),
            "char_count": len(text),
        })

    meta = {
        "company": args.company,
        "date": args.date,
        "keywords": args.keywords,
        "summary": {
            "total_files": total,
            "valid": valid,
            "duplicates": duplicates,
            "irrelevant": irrelevant,
        },
        "files": results,
    }

    meta_path = Path(args.meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[extract_and_filter] 완료: 전체 {total}건 → 유효 {valid}건 (중복 {duplicates}, 무관 {irrelevant})")
    print(f"  메타데이터: {meta_path}")


if __name__ == "__main__":
    main()
