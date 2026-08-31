"""
PDF/이미지 텍스트 추출 스크립트.
raw_reports/ 내 파일에서 텍스트를 추출하여 extracted_text/ 에 저장하고
collection_meta JSON의 extraction_status, quality_flag를 갱신한다.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

LOW_QUALITY_THRESHOLD = 200  # 텍스트 길이 < 200자 → low_quality


def extract_pdf_text(path: Path) -> tuple[str, str]:
    """PDF에서 텍스트 추출. (텍스트, extraction_type) 반환."""
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages).strip()
            if len(text) >= LOW_QUALITY_THRESHOLD:
                return text, "pdfplumber"
        except Exception:
            pass

    # pdfplumber 실패 또는 텍스트 부족 → OCR 시도
    if HAS_OCR:
        return extract_ocr_text(path), "ocr"

    return "", "failed"


def extract_ocr_text(path: Path) -> str:
    """Tesseract OCR로 텍스트 추출 (kor+eng)."""
    if not HAS_OCR:
        return ""
    try:
        # PDF의 경우 첫 페이지를 이미지로 변환
        if path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path
            images = convert_from_path(path, first_page=1, last_page=3)
        else:
            images = [Image.open(path)]

        texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="kor+eng")
            texts.append(text)
        return "\n".join(texts).strip()
    except Exception:
        return ""


def extract_text(path: Path) -> tuple[str, str]:
    """파일 유형에 따라 텍스트 추출. (텍스트, extraction_type) 반환."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(path)
    elif suffix in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
        text = extract_ocr_text(path)
        return text, ("ocr" if text else "failed")
    elif suffix == ".txt":
        try:
            return path.read_text(encoding="utf-8", errors="ignore"), "direct"
        except Exception:
            return "", "failed"
    else:
        return "", "skipped"


def update_meta(meta: dict, filename: str, extraction_type: str, text_len: int) -> None:
    for entry in meta.get("files", []):
        if entry["filename"] == filename:
            if extraction_type == "failed":
                entry["extraction_status"] = "failed"
            elif extraction_type == "ocr":
                entry["extraction_status"] = "ocr_only"
            elif extraction_type == "skipped":
                entry["extraction_status"] = "skipped"
            else:
                entry["extraction_status"] = "success"

            if text_len < LOW_QUALITY_THRESHOLD and extraction_type not in ("failed", "skipped"):
                entry["quality_flag"] = "low_quality"
            break


def main():
    parser = argparse.ArgumentParser(description="텍스트 추출")
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--text-dir", required=True)
    parser.add_argument("--meta-json", required=True)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    text_dir = Path(args.text_dir)
    meta_path = Path(args.meta_json)

    text_dir.mkdir(parents=True, exist_ok=True)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files = [e["filename"] for e in meta.get("files", [])]

    if not files:
        print("[extract_text] 처리할 파일 없음.")
        return

    success = 0
    for filename in files:
        src = raw_dir / filename
        if not src.exists():
            print(f"[extract_text] 파일 없음 스킵: {filename}")
            continue

        text, etype = extract_text(src)
        text_len = len(text.strip())

        dst = text_dir / (filename + ".txt")
        if text:
            dst.write_text(text, encoding="utf-8")
            if etype != "failed":
                success += 1
            print(f"[extract_text] {filename} → {etype} ({text_len}자)")
        else:
            print(f"[extract_text] {filename} → 추출 실패 ({etype})")

        update_meta(meta, filename, etype, text_len)

    total = len(files)
    meta["extraction_success"] = success
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    ratio = success / total if total > 0 else 0
    print(f"\n[extract_text] 추출 성공: {success}/{total} ({ratio:.0%})")

    if ratio < 0.5:
        print("[extract_text] WARN: 추출 성공률 50% 미만. OCR 환경을 확인하세요.")
        print("[extract_text] 에스컬레이션 필요. 추출된 파일만으로 분석 계속 진행.")


if __name__ == "__main__":
    main()
