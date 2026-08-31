"""
generate_md.py + generate_docx.js 순차 실행 래퍼.
에이전트가 Step 6 종합 분석 텍스트를 --summary-text로 전달한다.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent


def run_generate_md(analysis_dir: str, company: str, date_str: str,
                    summary_text: str = "") -> str:
    """generate_md.py 실행 → md 경로 반환."""
    md_path = os.path.join(analysis_dir, f"report_{date_str}_{company}.md")
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "generate_md.py"),
        "--analysis-dir", analysis_dir,
        "--company", company,
        "--date", date_str,
        "--output", md_path,
    ]
    if summary_text:
        cmd += ["--summary-text", summary_text]

    # 자식 파이썬이 UTF-8로 출력하도록 강제 (Windows cp949 불일치 방지)
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=child_env)
    if result.returncode != 0:
        print(f"[ERROR] generate_md.py 실패:\n{result.stderr}")
        raise RuntimeError("generate_md.py 실패")

    if result.stdout:
        print(result.stdout.strip())
    return md_path


def run_generate_docx(md_path: str, docx_path: str) -> bool:
    """generate_docx.js 실행 → 성공 여부 반환."""
    js_path = SCRIPTS_DIR / "generate_docx.js"

    # node 설치 확인
    try:
        node_check = subprocess.run(["node", "--version"],
                                    capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
        if node_check.returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        print("[WARN] node.js 미설치 — docx 생성 불가. md만 저장합니다.")
        return False

    # package.json / node_modules 확인
    pkg_json = SCRIPTS_DIR / "package.json"
    node_modules = SCRIPTS_DIR / "node_modules"
    if not node_modules.exists() and pkg_json.exists():
        print("[INFO] npm install 실행 중...")
        subprocess.run(["npm", "install"], cwd=str(SCRIPTS_DIR),
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")

    cmd = ["node", str(js_path), md_path, docx_path]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"[WARN] generate_docx.js 실패 (md는 저장됨):\n{result.stderr}")
        return False

    if result.stdout:
        print(result.stdout.strip())
    return True


def main():
    # 부모 콘솔(cp949)에서 유니코드 출력 시 크래시 방지
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--summary-text", default="")
    args = parser.parse_args()

    analysis_dir = args.analysis_dir
    company = args.company
    date_str = args.date

    print(f"\n[Step 7-1] Markdown 리포트 생성...")
    try:
        md_path = run_generate_md(analysis_dir, company, date_str, args.summary_text)
    except RuntimeError:
        print("[ERROR] Markdown 생성 실패 — 에이전트가 직접 md 작성 필요")
        return

    docx_path = os.path.join(analysis_dir, f"report_{date_str}_{company}.docx")
    print(f"\n[Step 7-2] Word 문서 생성...")
    success = run_generate_docx(md_path, docx_path)

    print(f"\n{'='*60}")
    print(f"[완료] 리포트 생성 결과")
    print(f"  MD : {md_path}")
    if success:
        print(f"  DOCX: {docx_path}")
    else:
        print(f"  DOCX: 생성 실패 (md만 저장)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
