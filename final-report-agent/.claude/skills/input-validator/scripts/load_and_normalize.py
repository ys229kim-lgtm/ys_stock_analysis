#!/usr/bin/env python3
"""
Step 1: 5개 에이전트 JSON 로딩 및 정규화
에이전트별 파싱 로직 분리 구현 — 키 이름·단위·구조 불일치 대응
출력: normalized_summary.json
"""
import argparse
import json
import sys
from pathlib import Path


# ─────────────────────────────────────────────
# 단위 헬퍼
# ─────────────────────────────────────────────

def to_uk(val):
    """숫자를 억원 단위로 반환. None/비숫자 시 None."""
    if val is None:
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    # 10조 이상이면 원 단위로 간주 → 억원 변환
    if abs(v) >= 10_000_000_000_000:
        return v / 100_000_000
    # 1조 이상이면 조원으로 간주 → 억원 변환
    if abs(v) >= 1_000_000_000_000:
        return v / 100_000_000
    return v


def safe_get(d: dict, *keys, default=None):
    """중첩 dict에서 키 체인으로 안전하게 값 추출."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
        if d is None:
            return default
    return d


def parse_pct(val, default=None):
    """'30%' / 0.3 / 30 형태를 0~1 비율(float)로 정규화."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val) / 100 if val > 1 else float(val)
    s = str(val).replace("%", "").strip()
    try:
        f = float(s)
        return f / 100 if f > 1 else f
    except ValueError:
        return default


# ─────────────────────────────────────────────
# 에이전트별 파서
# ─────────────────────────────────────────────

def parse_dart(data: dict) -> dict:
    """DART financial-analysis-agent 파서.

    실제 스키마: {unit, annual:[{year, income_statement, balance_sheet,
    cash_flow, derived_metrics}], growth_rates, red_flags, outlier_flags}
    """
    result = {
        "revenue_cagr_5y": None,
        "op_margin_latest": None,
        "net_margin_latest": None,
        "roe_latest": None,
        "debt_ratio_latest": None,
        "fcf_trend": None,
        "red_flags": [],
        "revenue_latest_uk": None,
        "op_profit_latest_uk": None,
    }
    if not data:
        return result
    try:
        # 단위 → 억원 환산 계수 (DART는 '조원' 단위로 산출)
        unit = (data.get("unit") or "").strip()
        if unit in ("조원", "조"):
            unit_to_uk = 10_000.0
        elif unit in ("억원", "억"):
            unit_to_uk = 1.0
        else:
            unit_to_uk = None  # 원 단위로 간주 → to_uk 사용

        annual = data.get("annual") or []
        latest = annual[-1] if annual else {}
        dm = latest.get("derived_metrics") or {}
        is_ = latest.get("income_statement") or {}

        # 성장성 (구버전 fallback 포함)
        gr = data.get("growth_rates") or {}
        result["revenue_cagr_5y"] = (
            gr.get("revenue_cagr_5y")
            or gr.get("revenue_cagr_3y")
            or safe_get(data, "summary", "revenue_cagr_5y")
        )

        # 최신 마진·수익성 지표 (derived_metrics 우선)
        result["op_margin_latest"] = dm.get("operating_margin")
        result["net_margin_latest"] = dm.get("net_margin")
        result["roe_latest"] = dm.get("roe")
        result["debt_ratio_latest"] = dm.get("debt_ratio")

        # Red flags
        flags = data.get("red_flags") or safe_get(data, "summary", "red_flags") or []
        result["red_flags"] = flags if isinstance(flags, list) else [flags]

        # FCF 추이 — annual derived_metrics.fcf 시계열에서 도출
        fcf_series = [
            (a.get("year"), (a.get("derived_metrics") or {}).get("fcf"))
            for a in annual
        ]
        fcf_vals = [(y, f) for y, f in fcf_series if f is not None]
        if fcf_vals:
            last_y, last_f = fcf_vals[-1]
            if len(fcf_vals) >= 2:
                prev_f = fcf_vals[-2][1]
                trend = "개선" if last_f > prev_f else "악화" if last_f < prev_f else "보합"
            else:
                trend = "단일연도"
            series_str = ", ".join(f"{y}:{f}" for y, f in fcf_vals)
            result["fcf_trend"] = (
                f"최근({last_y}) FCF {last_f}{unit or ''} ({trend}) | 추이 {series_str}"
            )

        # 최신 매출·영업이익 (억원)
        rev = is_.get("revenue")
        op = is_.get("operating_profit")
        if rev is not None and unit_to_uk is not None:
            result["revenue_latest_uk"] = round(rev * unit_to_uk, 1)
        else:
            result["revenue_latest_uk"] = to_uk(rev)
        if op is not None and unit_to_uk is not None:
            result["op_profit_latest_uk"] = round(op * unit_to_uk, 1)
        else:
            result["op_profit_latest_uk"] = to_uk(op)

    except Exception as e:
        print(f"[WARN] DART 파서 오류: {e}", file=sys.stderr)

    return result


def parse_telegram(data: dict) -> dict:
    """Telegram report-agent 파서.

    실제 스키마: {report_count_total, per_report:[{broker, investment_opinion,
    target_price, bullish_points, bearish_points, ...}]}
    """
    result = {
        "report_count": 0,
        "opinion_distribution": {"buy": 0, "hold": 0, "sell": 0},
        "tp_range": {"low": None, "high": None, "avg": None},
        "bullish_themes": [],
        "bearish_themes": [],
        "consensus_trend": None,
    }
    if not data:
        return result
    try:
        reports = data.get("per_report") or data.get("reports") or []
        # irrelevant=true 제외
        reports = [r for r in reports if isinstance(r, dict) and not r.get("irrelevant")]
        result["report_count"] = data.get("report_count_total") or len(reports)

        # opinion distribution — investment_opinion 문자열 정규화 집계
        buy = hold = sell = 0
        for r in reports:
            op = str(r.get("investment_opinion") or "").strip().lower()
            if "buy" in op or "매수" in op or "outperform" in op:
                buy += 1
            elif "hold" in op or "neutral" in op or "중립" in op or "marketperform" in op:
                hold += 1
            elif "sell" in op or "매도" in op or "reduce" in op or "underperform" in op:
                sell += 1
            # "overweight(섹터)" 등 섹터 등급은 종목 의견에서 제외
        result["opinion_distribution"] = {"buy": buy, "hold": hold, "sell": sell}

        # TP range — target_price 집계
        tps = [
            r.get("target_price") for r in reports
            if isinstance(r.get("target_price"), (int, float)) and r.get("target_price") > 0
        ]
        if tps:
            result["tp_range"]["low"] = min(tps)
            result["tp_range"]["high"] = max(tps)
            result["tp_range"]["avg"] = round(sum(tps) / len(tps))

        # 테마 — bullish/bearish_points 평탄화 + 중복 제거 (각 최대 15건)
        def collect(key):
            seen, out = set(), []
            for r in reports:
                pts = r.get(key) or []
                if not isinstance(pts, list):
                    pts = [pts]
                for p in pts:
                    if p and p not in seen:
                        seen.add(p)
                        out.append(p)
            return out[:15]

        result["bullish_themes"] = collect("bullish_points")
        result["bearish_themes"] = collect("bearish_points")
        result["consensus_trend"] = data.get("confidence_note")

    except Exception as e:
        print(f"[WARN] Telegram 파서 오류: {e}", file=sys.stderr)

    return result


def parse_news(data: dict) -> dict:
    """News analysis-agent 파서.

    실제 스키마: {events:[{cluster_title, category(positive/negative/
    neutral/future_plan), summary, ongoing, impact_magnitude, ...}]}
    """
    result = {
        "total_events": 0,
        "positive_events_count": 0,
        "negative_events_count": 0,
        "ongoing_risks": [],
        "key_future_plans": [],
        "sentiment_ratio": None,
    }
    if not data:
        return result
    try:
        events = data.get("events") or []
        result["total_events"] = len(events)

        pos = [e for e in events if e.get("category") == "positive"]
        neg = [e for e in events if e.get("category") == "negative"]
        plans = [e for e in events if e.get("category") == "future_plan"]
        result["positive_events_count"] = len(pos)
        result["negative_events_count"] = len(neg)

        # 진행 중 리스크 — 부정적 + ongoing=true
        result["ongoing_risks"] = [
            {
                "title": e.get("cluster_title") or e.get("summary"),
                "magnitude": e.get("impact_magnitude"),
                "scope": e.get("impact_scope"),
            }
            for e in neg
            if e.get("ongoing")
        ]

        # 주요 미래 계획 — future_plan 카테고리
        result["key_future_plans"] = [
            {
                "title": e.get("cluster_title") or e.get("summary"),
                "timeline": safe_get(e, "future_plan_details", "timeline"),
            }
            for e in plans
        ]

        # 심리 비율 — positive / (positive + negative)
        denom = len(pos) + len(neg)
        if denom > 0:
            result["sentiment_ratio"] = round(len(pos) / denom, 2)

    except Exception as e:
        print(f"[WARN] News 파서 오류: {e}", file=sys.stderr)

    return result


def parse_industry(data: dict) -> dict:
    """Industry analysis-agent 파서."""
    result = {
        "industry": None,
        "industry_tag": None,
        "short_term_base_growth": None,
        "mid_term_base_growth": None,
        "cycle_position": None,
        "value_chain_position": None,
        "scenario_probs": {
            "short": {"positive": 0.35, "base": 0.45, "negative": 0.20},
            "mid": {"positive": 0.40, "base": 0.40, "negative": 0.20},
        },
        "industry_data_available": False,
    }
    if not data:
        return result

    try:
        result["industry_data_available"] = True
        meta = data.get("meta") or {}
        # 사이클 블록 키 변형: supply_demand_cycle(대한항공형) / supply_demand(삼바형)
        sdc = data.get("supply_demand_cycle") or data.get("supply_demand") or {}

        result["industry"] = (
            meta.get("industry")
            or meta.get("industry_name")
            or data.get("industry")
        )
        result["industry_tag"] = (
            meta.get("industry_tag")
            or meta.get("tag")
            or data.get("industry_tag")
        )
        result["cycle_position"] = (
            sdc.get("current_phase")
            or sdc.get("current_cycle")
            or sdc.get("judgment")
            or safe_get(data, "cycle", "position")
        )
        result["value_chain_position"] = (
            meta.get("industry_level")
            or safe_get(data, "value_chain", "position")
        )

        # 시나리오 확률 — scenarios.short_term_1yr / mid_term_1_3yr 의
        # positive/base/negative.probability ('30%' 문자열) 파싱
        scen = data.get("scenarios") or {}

        def extract_probs(block, defaults):
            if not isinstance(block, dict):
                return defaults
            out = {}
            for k, dft in defaults.items():
                node = block.get(k) or {}
                out[k] = parse_pct(node.get("probability"), dft)
            return out

        # 시나리오 블록 키 변형: short_term_1yr(대한항공형) / short_term(삼바형)
        short_block = (
            scen.get("short_term_1yr") or scen.get("short_term") or scen.get("short") or {}
        )
        mid_block = (
            scen.get("mid_term_1_3yr") or scen.get("mid_term") or scen.get("mid") or {}
        )
        if short_block:
            result["scenario_probs"]["short"] = extract_probs(
                short_block, {"positive": 0.35, "base": 0.45, "negative": 0.20}
            )
        if mid_block:
            result["scenario_probs"]["mid"] = extract_probs(
                mid_block, {"positive": 0.40, "base": 0.40, "negative": 0.20}
            )

        # base 성장률은 산업 JSON에 수치 미제공 — narrative만 존재하므로 None 유지
        result["short_term_base_growth"] = safe_get(
            short_block, "base", "narrative"
        ) or result["short_term_base_growth"]
        result["mid_term_base_growth"] = safe_get(
            mid_block, "base", "narrative"
        ) or result["mid_term_base_growth"]

    except Exception as e:
        print(f"[WARN] Industry 파서 오류: {e}", file=sys.stderr)

    return result


def parse_valuation(val_results: dict, biz_model: dict, disclosures: dict, val_inputs: dict) -> dict:
    """Valuation-agent 파서 (4개 파일 통합)."""
    result = {
        "current_price": None,
        "industry_tag": None,
        "weighted_avg_fair_value": None,
        "fair_value_range": {"low": None, "high": None},
        "upside_pct": None,
        "valuation_methods": [],
        "consensus_target_price": None,
        "consensus_gap_pct": None,
        "ddm_applied": None,
        "high_disclosures": [],
        "wacc": None,
        "terminal_growth_rate": None,
        "biz_model_summary": None,
    }
    try:
        if val_results:
            result["current_price"] = val_results.get("current_price")
            result["industry_tag"] = val_results.get("industry_tag")
            result["ddm_applied"] = val_results.get("ddm_applied")

            # weighted_avg: {low, mid, high, upside_pct}
            wa = val_results.get("weighted_avg") or {}
            result["weighted_avg_fair_value"] = (
                wa.get("mid")
                or wa.get("weighted_avg_fair_value")
                or val_results.get("weighted_avg_fair_value")
            )
            result["fair_value_range"]["low"] = wa.get("low") or wa.get("min")
            result["fair_value_range"]["high"] = wa.get("high") or wa.get("max")
            result["upside_pct"] = wa.get("upside_pct") or val_results.get("upside_pct")

            # results: {dcf, per, pbr, psr, ev_ebitda, ddm, rim} → 리스트화
            res = val_results.get("results") or {}
            methods = []
            if isinstance(res, dict):
                for key, m in res.items():
                    if not isinstance(m, dict):
                        continue
                    methods.append({
                        "method": m.get("method") or key,
                        "low": m.get("low"),
                        "mid": m.get("mid"),
                        "high": m.get("high"),
                        "upside_pct": m.get("upside_pct"),
                        "applied": m.get("applied", True),
                    })
            elif isinstance(res, list):
                methods = res
            result["valuation_methods"] = methods

            # 컨센서스 비교
            cc = val_results.get("consensus_comparison") or {}
            result["consensus_target_price"] = cc.get("avg_target_price")
            result["consensus_gap_pct"] = cc.get("gap_pct")

        if disclosures:
            events = disclosures.get("events") or disclosures.get("disclosures") or []
            high = [
                e for e in events
                if isinstance(e, dict) and e.get("importance") == "high"
            ]
            # 별도 high 배열도 호환
            if not high:
                high = disclosures.get("high") or disclosures.get("high_disclosures") or []
            result["high_disclosures"] = high if isinstance(high, list) else []

        if val_inputs:
            result["wacc"] = (
                safe_get(val_inputs, "assumptions", "wacc")
                or val_inputs.get("wacc")
            )
            result["terminal_growth_rate"] = (
                safe_get(val_inputs, "assumptions", "terminal_growth_rate")
                or val_inputs.get("terminal_growth_rate")
                or val_inputs.get("perpetual_growth_rate")
            )

        if biz_model:
            result["biz_model_summary"] = {
                "pricing_power": safe_get(biz_model, "price_analysis", "pricing_power"),
                "price_summary": safe_get(biz_model, "price_analysis", "details"),
                "quantity_summary": safe_get(biz_model, "quantity_analysis", "details"),
                "cost_summary": safe_get(biz_model, "cost_analysis", "details"),
                "moat": safe_get(biz_model, "moat", "overall_grade"),
                "moat_rationale": safe_get(biz_model, "moat", "rationale"),
                "strengths": biz_model.get("strengths") or [],
                "weaknesses": biz_model.get("weaknesses") or [],
            }

    except Exception as e:
        print(f"[WARN] Valuation 파서 오류: {e}", file=sys.stderr)

    return result


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def resolve(base: Path, subdir: str, filename: str) -> Path:
    """서브폴더(output/)와 접미사가 붙은 파일명까지 탐색한다.

    telegram/news/industry 에이전트는 산출물을 {agent}/output/ 아래에 쓰고,
    industry는 파일명 끝에 산업명을 덧붙인다 (analysis_{date}_{company}_라면.json).
    """
    stem, ext = filename.rsplit(".", 1)
    for d in (base / subdir, base / subdir / "output"):
        exact = d / filename
        if exact.exists():
            return exact
        matches = sorted(d.glob(f"{stem}_*.{ext}"))
        if matches:
            return matches[0]
    return base / subdir / filename


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] JSON 로딩 실패 ({path}): {e}", file=sys.stderr)
        return None


def main():
    # Windows 콘솔(cp949)에서 유니코드(— 등) 출력 시 크래시 방지
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="5개 에이전트 JSON 로딩 및 정규화")
    parser.add_argument("--company", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--base-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    base = Path(args.base_path)
    out = Path(args.output_path)
    out.mkdir(parents=True, exist_ok=True)

    d, c = args.date, args.company

    # 파일 로딩
    dart_data = load_json(resolve(base, "financial", f"financials_{d}_{c}.json"))
    telegram_data = load_json(resolve(base, "telegram", f"analysis_{d}_{c}.json"))
    news_data = load_json(resolve(base, "news", f"analysis_{d}_{c}.json"))
    industry_data = load_json(resolve(base, "industry", f"analysis_{d}_{c}.json"))
    val_results = load_json(resolve(base, "valuation", f"val_results_{d}_{c}.json"))
    biz_model = load_json(resolve(base, "valuation", f"biz_model_{d}_{c}.json"))
    disclosures = load_json(resolve(base, "valuation", f"disclosures_{d}_{c}.json"))
    val_inputs = load_json(resolve(base, "valuation", f"val_inputs_{d}_{c}.json"))

    # 커버리지 확인
    data_coverage = {
        "dart": dart_data is not None,
        "telegram": telegram_data is not None,
        "news": news_data is not None,
        "industry": industry_data is not None,
        "valuation": val_results is not None,
    }

    # 에이전트별 파싱
    dart_summary = parse_dart(dart_data or {})
    telegram_summary = parse_telegram(telegram_data or {})
    news_summary = parse_news(news_data or {})
    industry_summary = parse_industry(industry_data or {})
    valuation_summary = parse_valuation(val_results or {}, biz_model or {}, disclosures or {}, val_inputs or {})

    # industry_tag 교차 보완: 산업 JSON에 없으면 valuation 산출물에서 채움
    if not industry_summary.get("industry_tag"):
        industry_summary["industry_tag"] = valuation_summary.get("industry_tag")

    # current_price: Valuation 우선, 없으면 DART에서 시도
    current_price = valuation_summary.get("current_price")

    normalized = {
        "company": c,
        "analysis_date": d,
        "current_price": current_price,
        "dart_summary": dart_summary,
        "telegram_summary": telegram_summary,
        "news_summary": news_summary,
        "industry_summary": industry_summary,
        "valuation_summary": valuation_summary,
        "data_coverage": data_coverage,
        "available_agent_count": sum(data_coverage.values()),
    }

    out_path = out / f"normalized_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print(json.dumps(normalized, ensure_ascii=False, indent=2))
    print(f"\n[OK] 정규화 완료: {out_path}", file=sys.stderr)
    print(f"[INFO] 활성 에이전트: {normalized['available_agent_count']}개 / 5개", file=sys.stderr)

    if normalized["available_agent_count"] <= 2:
        print("[ESCALATION] 활성 에이전트 2개 이하 — 최소 3개 필요합니다.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
