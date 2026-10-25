#!/usr/bin/env python3
"""
SEC EDGAR submissions API로 최근 공시 목록 수집 + 8-K Item 코드 중요도 분류 (한국판 disclosure-monitor 대응).

사용:
  SEC_USER_AGENT="Name email" uv run fetch_filings.py --ticker KBH --date 20261025 --output-dir <valuation 폴더> [--days 180]

출력: filings_{date}_{TICKER}.json
  - events: 8-K / 10-K / 10-Q / DEF 14A / SC 13D·13G / S-3·424B 등 (최신순), importance(high|medium|low), 원문 URL
  - form4_count: 기간 내 Form 4(내부자 거래) 건수 (매수/매도 방향은 원문 XML 확인 필요 - 에이전트가 필요 시 보완)
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_UA = "stock-analysis-agent research (set SEC_USER_AGENT env: Name email)"

ITEM_MAP = {
    "1.01": ("주요 계약 체결", "high"), "1.02": ("주요 계약 해지", "high"), "1.03": ("파산·회생", "high"),
    "1.05": ("사이버 보안 사고", "high"), "2.01": ("자산 인수·처분 완료", "high"),
    "2.02": ("실적 발표", "high"), "2.03": ("직접 금융채무 발생", "medium"),
    "2.04": ("채무 조건 가속", "high"), "2.05": ("구조조정 비용", "high"), "2.06": ("자산손상", "high"),
    "3.01": ("상장 요건 미충족", "high"), "3.02": ("비등록 증권 발행", "medium"),
    "3.03": ("주주 권리 변경", "medium"), "4.01": ("감사인 변경", "medium"),
    "4.02": ("재무제표 신뢰 철회(재작성)", "high"), "5.01": ("지배권 변경", "high"),
    "5.02": ("임원·이사 변동/보상", "high"), "5.03": ("정관 변경", "low"), "5.07": ("주주총회 결과", "medium"),
    "7.01": ("Reg FD 공시", "low"), "8.01": ("기타 사건", "medium"), "9.01": ("재무제표·첨부", "low"),
}
FORM_IMPORTANCE = {"10-K": "high", "10-K/A": "high", "10-Q": "high", "10-Q/A": "medium", "DEF 14A": "medium",
                   "SC 13D": "high", "SC 13D/A": "high", "SC 13G": "medium", "SC 13G/A": "medium",
                   "S-3": "medium", "S-3ASR": "medium", "424B5": "medium", "424B2": "medium", "S-8": "low",
                   "NT 10-K": "high", "NT 10-Q": "high", "11-K": "low"}


def http_json(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--days", type=int, default=180)
    a = ap.parse_args()
    ua = os.environ.get("SEC_USER_AGENT", DEFAULT_UA)
    if ua == DEFAULT_UA:
        print("[WARN] SEC_USER_AGENT 미설정 - SEC는 연락처 포함 User-Agent를 요구함", file=sys.stderr)

    tick = http_json("https://www.sec.gov/files/company_tickers.json", ua)
    row = next((v for v in tick.values() if v["ticker"].upper() == a.ticker.upper()), None)
    if not row:
        sys.exit(f"[ERROR] 티커를 찾지 못함: {a.ticker}")
    cik = row["cik_str"]
    sub = http_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", ua)
    rec = sub["filings"]["recent"]
    base_date = datetime.strptime(a.date, "%Y%m%d")
    cutoff = base_date - timedelta(days=a.days)

    events, form4 = [], 0
    for i, form in enumerate(rec["form"]):
        fdate = datetime.strptime(rec["filingDate"][i], "%Y-%m-%d")
        if fdate < cutoff or fdate > base_date + timedelta(days=1):
            continue
        if form == "4":
            form4 += 1
            continue
        if form not in FORM_IMPORTANCE and form != "8-K" and form != "8-K/A":
            continue
        acc = rec["accessionNumber"][i]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{rec['primaryDocument'][i]}"
        ev = {"date": rec["filingDate"][i], "form": form, "accession": acc, "url": url,
              "report_date": rec.get("reportDate", [None] * len(rec["form"]))[i]}
        if form.startswith("8-K"):
            items = [x.strip() for x in (rec["items"][i] or "").split(",") if x.strip()]
            ev["items"] = [{"code": c, "meaning": ITEM_MAP.get(c, ("기타", "low"))[0]} for c in items]
            levels = [ITEM_MAP.get(c, ("", "low"))[1] for c in items] or ["low"]
            ev["importance"] = "high" if "high" in levels else ("medium" if "medium" in levels else "low")
            # 9.01 / 7.01 만 있는 경우는 실적 첨부일 수 있으므로 low 로 두되 에이전트가 원문 확인
        else:
            ev["importance"] = FORM_IMPORTANCE[form]
        events.append(ev)

    events.sort(key=lambda e: e["date"], reverse=True)
    res = {
        "ticker": a.ticker.upper(), "company": sub.get("name"), "cik": f"{cik:010d}",
        "sic": sub.get("sic"), "sic_description": sub.get("sicDescription"),
        "fiscal_year_end": sub.get("fiscalYearEnd"), "state_of_incorporation": sub.get("stateOfIncorporation"),
        "collection_period": {"start": cutoff.strftime("%Y-%m-%d"), "end": base_date.strftime("%Y-%m-%d")},
        "counts": {"total": len(events),
                   "high": sum(e["importance"] == "high" for e in events),
                   "medium": sum(e["importance"] == "medium" for e in events),
                   "low": sum(e["importance"] == "low" for e in events)},
        "form4_count": form4,
        "events": events,
        "notes": ["importance 는 Item/서식 기반 1차 분류. 에이전트가 high 항목 원문을 읽고 valuation_impact(positive|neutral|negative)와 "
                  "impact_note를 직접 추가할 것.", "Form 4 매수/매도 방향은 미분류."],
    }
    outdir = Path(a.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / f"filings_{a.date}_{a.ticker.upper()}.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {p}", file=sys.stderr)
    print(json.dumps({"output": str(p), "counts": res["counts"], "form4": form4, "sic": sub.get("sicDescription")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
