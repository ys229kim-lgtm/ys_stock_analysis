# Skill: text-extractor

## 목적

`raw_reports/` 내 파일에서 텍스트를 추출하여 `extracted_text/`에 저장한다. PDF는 `pdfplumber`로 텍스트 레이어를 우선 추출하고 실패 시 `pytesseract` OCR로 재시도한다. 이미지 파일은 바로 OCR 처리한다.

## 트리거 조건

Step 2 (deduplicate.py) 완료 직후. `collection_meta` JSON이 존재해야 실행 가능.

---

## 스크립트

```
.claude/skills/text-extractor/scripts/extract_text.py
```

## 실행 방법

```bash
python extract_text.py \
  --raw-dir {raw_reports 경로} \
  --text-dir {extracted_text 경로} \
  --meta-json {collection_meta JSON 경로}
```

---

## 파일 유형별 처리

| 유형 | 처리 방법 | 실패 시 |
|------|----------|--------|
| PDF (텍스트 레이어) | `pdfplumber` 추출 | OCR 시도 |
| PDF (스캔 이미지) | `pytesseract` OCR (kor+eng) | 메타만 기록, 스킵 |
| JPG / PNG / 이미지 | `pytesseract` OCR (kor+eng) | 메타만 기록, 스킵 |
| .txt | 직접 읽기 | — |

**품질 플래그 기준:**
- 추출된 텍스트 길이 < 200자 → `quality_flag: "low_quality"` 부여
- OCR로만 추출 성공 → `extraction_status: "ocr_only"`

---

## 출력

- `extracted_text/{원본파일명}.txt` (파일당 1개)
- `collection_meta` JSON의 `extraction_status`, `quality_flag` 필드 갱신
- `extraction_success` 카운트 갱신

---

## 성공 기준

- 전체 파일 중 **50% 이상** 텍스트 추출 성공

## 실패 처리

- 성공률 < 50% → 에스컬레이션 (OCR 환경 확인 요청)
- 에스컬레이션 후에도 추출된 파일만으로 Step 4 분석 계속 진행

---

## 의존성

```
pdfplumber>=0.11
pytesseract>=0.3.10
Pillow>=10.0
```

Tesseract 바이너리와 한국어 언어팩(`kor`) 별도 설치 필요:
- Ubuntu: `apt-get install tesseract-ocr tesseract-ocr-kor`
- Windows: [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 설치 후 PATH 설정
