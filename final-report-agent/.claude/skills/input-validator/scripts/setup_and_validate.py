#!/usr/bin/env python3
"""
Step 0: 출력 폴더 생성 + 입력 파일 검증
필수 파일(DART + Valuation) 누락 시 exit(1) 에스컬레이션
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


REQUIRED_FILES = {
    "DART_financials": "financial/financials_{date}_{company}.json",
    "Valuation_val_results": "valuation/val_results_{date}_{company}.json",
}

OPTIONAL_FILES = {
    "Telegram_analysis": "telegram/analysis_{date}_{company}.json",
    "News_analysis": "news/analysis_{date}_{company}.json",
    "Industry_analysis": "industry/analysis_{date}_{company}.json",
    "Valuation_biz_model": "valuation/biz_model_{date}_{company}.json",
    "Valuation_disclosures": "valuation/disclosures_{date}_{company}.json",
    "Valuation_val_inputs": "valuation/val_inputs_{date}_{company}.json",
}


def resolve_path(base: Path, template: str, date: str, company: str) -> Path:
    """서브폴더(output/)와 접미사가 붙은 파일명까지 탐색한다.

    telegram/news/industry 에이전트는 산출물을 {agent}/output/ 아래에 쓰고,
    industry는 파일명 끝에 산업명을 덧붙인다 (analysis_{date}_{company}_라면.json).
    """
    rel = template.format(date=date, company=company)
    subdir, _, filename = rel.rpartition("/")
    stem, ext = filename.rsplit(".", 1)

    for d in (base / subdir, base / subdir / "output"):
        exact = d / filename
        if exact.exists():
            return exact
        matches = sorted(d.glob(f"{stem}_*.{ext}"))
        if matches:
            return matches[0]

    return base / rel


def main():
    parser = argparse.ArgumentParser(description="최종 리포트 에이전트 - 입력 검증 및 폴더 생성")
    parser.add_argument("--company", required=True, help="기업명 (한글)")
    parser.add_argument("--date", required=True, help="날짜 YYYYMMDD")
    parser.add_argument("--base-path", required=True, help="기업별 날짜 폴더 경로")
    args = parser.parse_args()

    base = Path(args.base_path)
    output_dir = base / "final"
    output_dir.mkdir(parents=True, exist_ok=True)

    present_files = {}
    missing_required = []
    missing_optional = []

    for name, template in REQUIRED_FILES.items():
        path = resolve_path(base, template, args.date, args.company)
        if path.exists():
            present_files[name] = str(path)
        else:
            missing_required.append({"name": name, "path": str(path)})

    for name, template in OPTIONAL_FILES.items():
        path = resolve_path(base, template, args.date, args.company)
        if path.exists():
            present_files[name] = str(path)
        else:
            missing_optional.append({"name": name, "path": str(path)})

    # missing_inputs.log 기록
    log_path = output_dir / "missing_inputs.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"=== 입력 파일 검증 결과 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n\n")
        f.write(f"기업명: {args.company} | 날짜: {args.date}\n")
        f.write(f"base_path: {base}\n\n")

        f.write("[ 존재하는 파일 ]\n")
        for name, path in present_files.items():
            f.write(f"  ✓ {name}: {path}\n")
        f.write("\n")

        if missing_required:
            f.write("[ 누락된 필수 파일 - 에스컬레이션 필요 ]\n")
            for item in missing_required:
                f.write(f"  ✗ {item['name']}: {item['path']}\n")
            f.write("\n")

        if missing_optional:
            f.write("[ 누락된 선택 파일 - 해당 섹션 데이터 없음 처리 ]\n")
            for item in missing_optional:
                f.write(f"  - {item['name']}: {item['path']}\n")

    result = {
        "output_dir": str(output_dir),
        "present_files": present_files,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "can_proceed": len(missing_required) == 0,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if missing_required:
        print("\n[ESCALATION] 필수 파일 누락 — 아래 에이전트를 먼저 실행하세요:", file=sys.stderr)
        agent_map = {
            "DART_financials": "financial-analysis-agent",
            "Valuation_val_results": "valuation-agent",
        }
        for item in missing_required:
            agent = agent_map.get(item["name"], item["name"])
            print(f"  → {agent} 실행 필요: {item['path']}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[OK] 출력 폴더 준비 완료: {output_dir}", file=sys.stderr)
    if missing_optional:
        print(
            f"[INFO] 선택 파일 {len(missing_optional)}개 누락 — 해당 섹션 '데이터 없음' 처리됩니다.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
