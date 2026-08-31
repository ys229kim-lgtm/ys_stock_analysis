"""
Step 4.5: analysis JSON 구조 체크리스트 자동 검증
Usage: python validate_analysis.py --json_path ./output/analysis_20260608_삼성전자_반도체.json
"""
import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = [
    "overview",
    "market_size",
    "competition",
    "supply_demand",
    "global_trends",
    "regulation",
    "scenarios",
]

REQUIRED_SCENARIO_KEYS = ["positive", "base", "negative"]
REQUIRED_HORIZON_KEYS = ["short_term", "mid_term"]


def extract_probability_value(prob_str: str) -> float | None:
    """
    확률 문자열에서 숫자 추출.
    예: "35%" → 35.0
        "30~45%" → 37.5 (중간값)
        "35% (데이터 부족 추정값)" → 35.0
    """
    # 범위 표기 (30~45%)
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[~\-]\s*(\d+(?:\.\d+)?)", prob_str)
    if range_match:
        lo, hi = float(range_match.group(1)), float(range_match.group(2))
        return (lo + hi) / 2

    # 단일 값
    single_match = re.search(r"(\d+(?:\.\d+)?)\s*%", prob_str)
    if single_match:
        return float(single_match.group(1))

    return None


def check_probability_sum(scenarios: dict, horizon: str) -> tuple[bool, float, str]:
    """3개 시나리오 확률 합계 = 100% 검증. (통과여부, 합계, 오류메시지)"""
    total = 0.0
    missing = []
    for key in REQUIRED_SCENARIO_KEYS:
        scenario = scenarios.get(key, {})
        prob_raw = scenario.get("probability", "")
        val = extract_probability_value(str(prob_raw))
        if val is None:
            missing.append(key)
        else:
            total += val

    if missing:
        return False, total, f"[{horizon}] 확률 값 파싱 불가: {missing}"

    # 반올림 오차 허용 ±1
    if abs(total - 100.0) > 1.0:
        return False, total, f"[{horizon}] 확률 합계 = {total:.1f}% (100% 필요)"

    return True, total, ""


def validate(data: dict) -> list[str]:
    """검증 실패 목록 반환. 빈 리스트면 통과."""
    errors = []

    # 1. 7대 영역 키 존재
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            errors.append(f"누락된 최상위 키: '{key}'")

    # 2. scenarios 구조
    scenarios = data.get("scenarios", {})
    for horizon_key in REQUIRED_HORIZON_KEYS:
        horizon = scenarios.get(horizon_key, {})
        if not horizon:
            errors.append(f"scenarios.{horizon_key} 누락")
            continue
        for sk in REQUIRED_SCENARIO_KEYS:
            if sk not in horizon:
                errors.append(f"scenarios.{horizon_key}.{sk} 누락")

        # 3. 확률 합계
        ok, total, msg = check_probability_sum(horizon, horizon_key)
        if not ok:
            errors.append(msg)

    # 4. target_company_position
    overview = data.get("overview", {})
    if not overview.get("target_company_position"):
        errors.append("overview.target_company_position 값 없음")

    # 5. 수치에 source 또는 label 존재 (market_size)
    market_size = data.get("market_size", {})
    if market_size and not market_size.get("source") and not market_size.get("label"):
        errors.append("market_size.source 또는 market_size.label 없음")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", required=True)
    parser.add_argument("--strict", action="store_true", help="오류 시 exit code 1 반환")
    args = parser.parse_args()

    path = Path(args.json_path)
    if not path.exists():
        print(f"[validate] 파일 없음: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[validate] JSON 파싱 오류: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(data)

    if not errors:
        print("[validate] ✅ 모든 체크리스트 통과")
        sys.exit(0)
    else:
        print(f"[validate] ❌ {len(errors)}개 항목 실패:")
        for err in errors:
            print(f"  - {err}")
        if args.strict:
            sys.exit(1)


if __name__ == "__main__":
    main()
