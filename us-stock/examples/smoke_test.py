#!/usr/bin/env python3
"""
오프라인 회귀 테스트: examples/KBH_20261025 의 고정 입력으로 검증·계산 스크립트를 재실행해 기대값과 비교한다.
(네트워크 수집 스크립트 fetch_sec / fetch_quote / fetch_fred / fetch_filings 는 포함하지 않음 - 라이브 호출이므로 별도 점검)

사용:  uv run python -I C:/claude/stock/us-stock/examples/smoke_test.py
기대:  밸류에이션 가중 평균 40.06 / 49.44 / 57.95, 시나리오 확률 26/51/23, validate_report 전 항목 PASS
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples" / "KBH_20261025"
PY = [sys.executable, "-X", "utf8", "-I"]
env_utf8 = {"PYTHONUTF8": "1"}


def run(args, **kw):
    import os
    env = {**os.environ, **env_utf8}
    return subprocess.run(PY + args, capture_output=True, text=True, encoding="utf-8", env=env, **kw)


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    return ok


def main():
    tmp = Path(tempfile.mkdtemp(prefix="us_smoke_"))
    results = []

    # 1) 밸류에이션 엔진
    val_out = tmp / "val_results.json"
    r = run([str(ROOT / "us-valuation-agent/.claude/skills/valuation-engine/scripts/calculate_valuation.py"),
             "--val-inputs", str(EX / "valuation/val_inputs_20261025_KBH.json"), "--output", str(val_out)])
    ok = r.returncode == 0
    if ok:
        w = json.loads(val_out.read_text(encoding="utf-8"))["weighted_avg"]
        ok = (w["low"], w["mid"], w["high"]) == (40.06, 49.44, 57.95)
        results.append(check("valuation weighted avg 40.06/49.44/57.95", ok, str(w)))
    else:
        results.append(check("valuation engine runs", False, r.stderr[-300:]))

    # 2) 시나리오 빌더
    sc_out = tmp / "scenarios.json"
    r = run([str(ROOT / "us-final-report-agent/.claude/skills/scenario-builder/scripts/build_scenarios.py"),
             "--val-results", str(val_out), "--tp-high", "70", "--negative-floor", "34",
             "--negative-basis", "Argus lowest target", "--adjustments", str(EX / "final/adjustments.json"),
             "--output", str(sc_out)])
    if r.returncode == 0:
        p = {k: v["probability"] for k, v in json.loads(sc_out.read_text(encoding="utf-8"))["scenarios"].items()}
        results.append(check("scenario probs 26/51/23", p == {"positive": 0.26, "base": 0.51, "negative": 0.23}, str(p)))
    else:
        results.append(check("scenario builder runs", False, r.stderr[-300:]))

    # 3) 규칙 위반 감지 (보정 합계 != 0)
    bad = tmp / "bad.json"
    bad.write_text(json.dumps([{"signal": "x", "target": "positive", "delta_pp": -3}]), encoding="utf-8")
    r = run([str(ROOT / "us-final-report-agent/.claude/skills/scenario-builder/scripts/build_scenarios.py"),
             "--val-results", str(val_out), "--tp-high", "70", "--negative-floor", "34", "--negative-basis", "x",
             "--adjustments", str(bad), "--output", str(tmp / "x.json")])
    results.append(check("scenario builder rejects unbalanced adjustments", r.returncode != 0))

    # 4) 정규화 + 리포트 검증
    r = run([str(ROOT / "us-final-report-agent/.claude/skills/input-validator/scripts/setup_and_normalize.py"),
             "--ticker", "KBH", "--company", "KB Home", "--date", "20261025", "--base-path", str(EX)])
    results.append(check("setup_and_normalize (5/5 coverage)", r.returncode == 0 and "5/5" in ((r.stderr or "") + (r.stdout or "")),
                         ((r.stderr or '') + (r.stdout or ''))[-120:]))
    r = run([str(ROOT / "us-final-report-agent/.claude/skills/report-builder/scripts/validate_report.py"),
             "--report", str(EX / "final/report_20261025_KB Home.md"), "--scenarios", str(EX / "final/scenarios.json")])
    results.append(check("validate_report all PASS", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:]))

    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
