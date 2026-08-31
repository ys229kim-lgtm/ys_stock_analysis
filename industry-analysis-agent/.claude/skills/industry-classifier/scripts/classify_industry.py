"""
Step 0: yfinance + DART 기반 산업 분류
Usage: python classify_industry.py --company 삼성전자 --code 005930
"""
import argparse
import json
import sys

# yfinance는 환경에 설치되어 있어야 함
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


KOSPI_SUFFIX = ".KS"
KOSDAQ_SUFFIX = ".KQ"


def try_yfinance(code: str, company: str) -> dict | None:
    """yfinance로 섹터·산업 조회. 실패 또는 Unknown 반환 시 None."""
    if not YFINANCE_AVAILABLE:
        return None

    tickers_to_try = []
    if code:
        tickers_to_try += [f"{code}{KOSPI_SUFFIX}", f"{code}{KOSDAQ_SUFFIX}"]
    if company:
        # 영문명이 있으면 직접 시도
        tickers_to_try.append(company)

    for ticker_str in tickers_to_try:
        try:
            t = yf.Ticker(ticker_str)
            info = t.info
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            long_name = info.get("longName", "")

            if sector and sector.lower() not in ("unknown", "n/a", ""):
                return {
                    "ticker": ticker_str,
                    "sector": sector,
                    "industry": industry,
                    "longName": long_name,
                    "source": "yfinance",
                }
        except Exception:
            continue

    return None


def parse_dart_business_text(text: str) -> dict:
    """사업보고서 '사업의 개요' 텍스트에서 산업명 힌트 추출 (LLM이 최종 판단)."""
    # LLM에게 전달할 텍스트를 500자로 잘라 반환
    snippet = text[:500] if text else ""
    return {
        "source": "dart_business_info",
        "snippet": snippet,
        "note": "LLM이 이 텍스트를 기반으로 산업명을 추론해야 합니다.",
    }


def build_classification_result(yf_result: dict | None, dart_result: dict | None, company: str) -> dict:
    result = {
        "company": company,
        "yfinance": yf_result,
        "dart": dart_result,
        "classification_status": "unknown",
        "suggested_industry": None,
        "suggested_segment": None,
    }

    if yf_result:
        result["classification_status"] = "yfinance_success"
        result["suggested_industry"] = yf_result.get("sector")
        result["suggested_segment"] = yf_result.get("industry")
    elif dart_result:
        result["classification_status"] = "dart_fallback"
        # 실제 산업명 추론은 LLM 몫
    else:
        result["classification_status"] = "llm_inference_required"

    return result


def main():
    parser = argparse.ArgumentParser(description="산업 분류 조회")
    parser.add_argument("--company", required=True, help="기업명 (한글)")
    parser.add_argument("--code", default="", help="종목코드 6자리")
    parser.add_argument("--dart_text", default="", help="DART 사업의 개요 텍스트 (선택)")
    args = parser.parse_args()

    yf_result = try_yfinance(args.code, args.company)

    dart_result = None
    if not yf_result and args.dart_text:
        dart_result = parse_dart_business_text(args.dart_text)

    result = build_classification_result(yf_result, dart_result, args.company)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
