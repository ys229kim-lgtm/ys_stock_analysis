#!/usr/bin/env python3
"""
generate_charts.py — 재무 시각화 차트 생성 (matplotlib, 한국형 스타일)

Usage:
    python generate_charts.py --input financials.json --output-dir charts/
    python generate_charts.py --input financials.json \
        --competitors comp1.json comp2.json --output-dir charts/
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import numpy as np


# ── 한글 폰트 설정 ────────────────────────────────────────────────────────
def setup_korean_font() -> str:
    candidates = ["NanumGothic", "AppleGothic", "Malgun Gothic", "DejaVu Sans"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    print("[WARN] 한글 폰트 미설치 — 레이블을 영문으로 표시합니다.", file=sys.stderr)
    return "DejaVu Sans"


# ── 색상 팔레트 (한국형 FnGuide/KIS 스타일) ─────────────────────────────
C = {
    "revenue":   "#1F3A93",
    "op_profit": "#1E8449",
    "net_income":"#CA6F1E",
    "roe":       "#8E44AD",
    "roa":       "#2980B9",
    "fcf":       "#16A085",
    "debt":      "#C0392B",
    "current":   "#27AE60",
    "interest":  "#F39C12",
    "ocf":       "#2471A3",
    "icf":       "#E74C3C",
    "ffcf":      "#28B463",
    "comp":      ["#1F3A93", "#C0392B", "#1E8449", "#8E44AD"],
}
SPINE_W = 1.5
GRID_C  = "#E8E8E8"
FS      = {"title": 12, "axis": 9, "tick": 8, "legend": 8}


def apply_style(ax):
    ax.set_facecolor("white")
    ax.grid(axis="y", color=GRID_C, linewidth=0.8, zorder=0)
    for sp in ax.spines.values():
        sp.set_linewidth(SPINE_W)
    ax.tick_params(labelsize=FS["tick"])


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def gv(item, *keys):
    v = item
    for k in keys:
        v = v.get(k) if isinstance(v, dict) else None
        if v is None:
            return None
    return v


def ylabels(annual): return [str(a.get("year", "")) for a in annual]


# ── Chart 01 ─────────────────────────────────────────────────────────────
def c01(annual, out, name):
    ys = ylabels(annual)
    rev = [gv(a,"income_statement","revenue")        for a in annual]
    op  = [gv(a,"income_statement","operating_profit") for a in annual]
    ni  = [gv(a,"income_statement","net_income")     for a in annual]
    x, w = np.arange(len(ys)), 0.28
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x-w, rev, w, label="Revenue (매출액)",           color=C["revenue"],   zorder=3)
    ax.bar(x,   op,  w, label="Operating Profit (영업이익)", color=C["op_profit"], zorder=3)
    ax.bar(x+w, ni,  w, label="Net Income (순이익)",         color=C["net_income"],zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(ys)
    ax.set_ylabel("조원")
    ax.set_title(f"{name} | Revenue & Profit Trend (매출·이익 추이)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "01_revenue_profit_trend.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 02 ─────────────────────────────────────────────────────────────
def c02(annual, out, name):
    ys = ylabels(annual)
    opm = [gv(a,"derived_metrics","operating_margin") for a in annual]
    nm  = [gv(a,"derived_metrics","net_margin")       for a in annual]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(ys, opm, marker="o", color=C["op_profit"], lw=2, label="Operating Margin (영업이익률)")
    ax.plot(ys, nm,  marker="s", color=C["net_income"],lw=2, label="Net Margin (순이익률)")
    ax.set_ylabel("%"); ax.set_title(f"{name} | Margin Trend (이익률 추이)", fontsize=FS["title"])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "02_margin_trend.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 03 ─────────────────────────────────────────────────────────────
def c03(annual, out, name):
    ys  = ylabels(annual)
    roe = [gv(a,"derived_metrics","roe") for a in annual]
    roa = [gv(a,"derived_metrics","roa") for a in annual]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(ys, roe, marker="o", color=C["roe"], lw=2, label="ROE")
    ax.plot(ys, roa, marker="s", color=C["roa"], lw=2, label="ROA")
    ax.axhline(0, color="gray", lw=0.8, ls="--")
    ax.set_ylabel("%"); ax.set_title(f"{name} | ROE / ROA Trend", fontsize=FS["title"])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "03_roe_roa_trend.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 04 ─────────────────────────────────────────────────────────────
def c04(annual, out, name):
    ys   = ylabels(annual)
    dr   = [gv(a,"derived_metrics","debt_ratio")        for a in annual]
    cr   = [gv(a,"derived_metrics","current_ratio")     for a in annual]
    ic   = [gv(a,"derived_metrics","interest_coverage") or 0 for a in annual]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, vals, lbl, color, ref in [
        (axes[0], dr, "Debt Ratio\n(부채비율, %)",         C["debt"],    200),
        (axes[1], cr, "Current Ratio\n(유동비율, %)",       C["current"], 100),
        (axes[2], ic, "Interest Coverage\n(이자보상배율, x)",C["interest"], 2),
    ]:
        ax.bar(ys, vals, color=color, alpha=0.85, zorder=3)
        ax.axhline(ref, color="red", lw=1, ls="--", label=f"기준선 {ref}")
        ax.set_title(lbl, fontsize=FS["axis"]); ax.tick_params(axis="x", rotation=45, labelsize=7)
        apply_style(ax); ax.legend(fontsize=7)
    fig.suptitle(f"{name} | Stability Indicators (안정성 지표)", fontsize=FS["title"])
    fig.tight_layout()
    p = Path(out) / "04_debt_stability.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 05 ─────────────────────────────────────────────────────────────
def c05(annual, out, name):
    ys = ylabels(annual)
    ocf  = [gv(a,"cash_flow","operating_cf")  for a in annual]
    icf  = [gv(a,"cash_flow","investing_cf")  for a in annual]
    ffcf = [gv(a,"cash_flow","financing_cf")  for a in annual]
    x, w = np.arange(len(ys)), 0.28
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x-w, ocf,  w, label="Operating CF (영업CF)",  color=C["ocf"],  zorder=3)
    ax.bar(x,   icf,  w, label="Investing CF (투자CF)",  color=C["icf"],  zorder=3)
    ax.bar(x+w, ffcf, w, label="Financing CF (재무CF)",  color=C["ffcf"], zorder=3)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(ys)
    ax.set_ylabel("조원")
    ax.set_title(f"{name} | Cash Flow Breakdown (현금흐름 분해)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "05_cashflow_breakdown.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 06 ─────────────────────────────────────────────────────────────
def c06(annual, out, name):
    ys   = ylabels(annual)
    fcf  = [gv(a,"derived_metrics","fcf")       for a in annual]
    fcfm = [gv(a,"derived_metrics","fcf_margin") for a in annual]
    fig, ax1 = plt.subplots(figsize=(11, 4))
    ax2 = ax1.twinx()
    ax1.bar(ys, fcf, color=C["fcf"], alpha=0.75, label="FCF (조원)", zorder=3)
    ax2.plot(ys, fcfm, marker="o", color=C["revenue"], lw=2, label="FCF Margin (%)")
    ax1.axhline(0, color="red", lw=0.8, ls="--")
    ax1.set_ylabel("조원"); ax2.set_ylabel("%")
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax1.set_title(f"{name} | FCF Trend (잉여현금흐름)", fontsize=FS["title"])
    l1, n1 = ax1.get_legend_handles_labels()
    l2, n2 = ax2.get_legend_handles_labels()
    ax1.legend(l1+l2, n1+n2, fontsize=FS["legend"]); apply_style(ax1); fig.tight_layout()
    p = Path(out) / "06_fcf_trend.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 07 ─────────────────────────────────────────────────────────────
def c07(annual, out, name, growth):
    ys   = [str(y) for y in growth.get("years", [a["year"] for a in annual])]
    ryoy = growth.get("revenue_yoy", [])
    oyoy = growth.get("op_profit_yoy", [])
    # Replace None with 0 for plotting
    ryoy_plot = [v if v is not None else 0 for v in ryoy]
    oyoy_plot = [v if v is not None else 0 for v in oyoy]
    x, w = np.arange(len(ys)), 0.35
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(x-w/2, ryoy_plot, w, label="Revenue YoY (매출 성장률, %)",          color=C["revenue"],   alpha=0.85, zorder=3)
    ax.bar(x+w/2, oyoy_plot, w, label="Op.Profit YoY (영업이익 성장률, %)",    color=C["op_profit"], alpha=0.85, zorder=3)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(ys)
    ax.set_ylabel("%"); ax.set_title(f"{name} | YoY Growth Rate (연간 성장률)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "07_growth_rate.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Chart 08 ─────────────────────────────────────────────────────────────
def c08(segments, out, name, latest_year):
    seg = [s for s in segments if s.get("year") == latest_year]
    if not seg:
        return None
    labels = [s.get("segment_name","기타") for s in seg]
    sizes  = [s.get("ratio") or s.get("revenue") or 0 for s in seg]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=plt.cm.Set2.colors, textprops={"fontsize": 8})
    ax.set_title(f"{name} | Segment Revenue Mix (사업부문 비중, {latest_year})", fontsize=FS["title"])
    fig.tight_layout()
    p = Path(out) / "08_segment_revenue.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── Charts 09~12 ─────────────────────────────────────────────────────────
def _comp_years(all_data, n=5):
    return sorted({a["year"] for d in all_data for a in d["annual"]})[-n:]


def c09(main, comps, out):
    names    = [main["company"]["name"]] + [c["company"]["name"] for c in comps]
    all_data = [main] + comps
    ys = _comp_years(all_data)
    x, w = np.arange(len(ys)), 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (nm, d) in enumerate(zip(names, all_data)):
        ym = {a["year"]: gv(a,"derived_metrics","operating_margin") for a in d["annual"]}
        vals = [ym.get(y) if ym.get(y) is not None else 0 for y in ys]
        ax.bar(x + i*w - (len(names)-1)*w/2, vals, w,
               label=nm, color=C["comp"][i%4], zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([str(y) for y in ys])
    ax.set_ylabel("%"); ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.set_title("Operating Margin Comparison (영업이익률 비교)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "09_competitor_margin.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


def c10(main, comps, out):
    names    = [main["company"]["name"]] + [c["company"]["name"] for c in comps]
    all_data = [main] + comps
    ys = _comp_years(all_data)
    x, w = np.arange(len(ys)), 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (nm, d) in enumerate(zip(names, all_data)):
        ann = sorted(d["annual"], key=lambda a: a["year"])
        yoy = {}
        for j in range(1, len(ann)):
            p = gv(ann[j-1],"income_statement","revenue")
            c = gv(ann[j],  "income_statement","revenue")
            if p and p != 0 and c is not None:
                yoy[ann[j]["year"]] = (c - p) / abs(p) * 100
        vals_yoy = [yoy.get(y) if yoy.get(y) is not None else 0 for y in ys]
        ax.bar(x + i*w - (len(names)-1)*w/2, vals_yoy, w,
               label=nm, color=C["comp"][i%4], zorder=3)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([str(y) for y in ys])
    ax.set_ylabel("%"); ax.set_title("Revenue Growth Rate Comparison (매출 성장률 비교)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "10_competitor_growth.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


def c11(main, comps, out):
    names    = [main["company"]["name"]] + [c["company"]["name"] for c in comps]
    all_data = [main] + comps
    metrics  = ["부채비율\n(역수)", "유동비율", "이자보상배율", "ROE", "FCF 마진"]
    n = len(metrics)

    def normalize(d):
        ann = sorted(d["annual"], key=lambda a: a["year"])
        if not ann: return [0]*n
        m = ann[-1]["derived_metrics"]
        return [
            max(0, 100 - min(m.get("debt_ratio")    or 0, 300)) / 3,
            min(m.get("current_ratio")               or 0, 300) / 3,
            min(max(m.get("interest_coverage")       or 0, 0), 10) * 10,
            min(max(m.get("roe")                     or 0, 0), 30) / 0.3,
            min(max((m.get("fcf_margin")             or 0) * 100, 0), 20) * 5,
        ]

    angles = [i / n * 2 * np.pi for i in range(n)] + [0]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, (nm, d) in enumerate(zip(names, all_data)):
        v = normalize(d) + [normalize(d)[0]]
        ax.plot(angles, v, lw=2, color=C["comp"][i%4], label=nm)
        ax.fill(angles, v, alpha=0.08, color=C["comp"][i%4])
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(metrics, fontsize=8)
    ax.set_title("Stability Comparison (안정성 비교)", pad=20, fontsize=FS["title"])
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=FS["legend"])
    fig.tight_layout()
    p = Path(out) / "11_competitor_stability.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


def c12(main, comps, out):
    names    = [main["company"]["name"]] + [c["company"]["name"] for c in comps]
    all_data = [main] + comps
    ys = _comp_years(all_data)
    x, w = np.arange(len(ys)), 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (nm, d) in enumerate(zip(names, all_data)):
        ym = {a["year"]: gv(a,"derived_metrics","fcf") for a in d["annual"]}
        vals_fcf = [ym.get(y) if ym.get(y) is not None else 0 for y in ys]
        ax.bar(x + i*w - (len(names)-1)*w/2, vals_fcf, w,
               label=nm, color=C["comp"][i%4], zorder=3)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([str(y) for y in ys])
    ax.set_ylabel("조원"); ax.set_title("FCF Comparison (잉여현금흐름 비교)", fontsize=FS["title"])
    ax.legend(fontsize=FS["legend"]); apply_style(ax); fig.tight_layout()
    p = Path(out) / "12_competitor_cashflow.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); return p


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",       required=True)
    parser.add_argument("--competitors", nargs="*", default=[])
    parser.add_argument("--output-dir",  required=True)
    args = parser.parse_args()

    setup_korean_font()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md   = load(args.input)
    cds  = [load(p) for p in args.competitors]
    ann  = md.get("annual", [])
    name = md["company"]["name"]
    segs = md.get("segments", [])
    grw  = md.get("growth_rates", {})
    ly   = ann[-1]["year"] if ann else None

    gen, skipped = [], []

    def try_chart(fn, label, *a, **kw):
        try:
            path = fn(*a, **kw)
            if path and Path(path).stat().st_size > 10_240:
                gen.append(label); print(f"[OK] {label}")
            else:
                skipped.append(label); print(f"[SKIP] {label} - file too small")
        except Exception as e:
            skipped.append(label); print(f"[SKIP] {label} - {e}", file=sys.stderr)

    try_chart(c01, "01_revenue_profit_trend", ann, out, name)
    try_chart(c02, "02_margin_trend",         ann, out, name)
    try_chart(c03, "03_roe_roa_trend",        ann, out, name)
    try_chart(c04, "04_debt_stability",       ann, out, name)
    try_chart(c05, "05_cashflow_breakdown",   ann, out, name)
    try_chart(c06, "06_fcf_trend",            ann, out, name)
    try_chart(c07, "07_growth_rate",          ann, out, name, grw)

    if segs and ly:
        try_chart(c08, "08_segment_revenue", segs, out, name, ly)
    else:
        skipped.append("08_segment_revenue")
        print("[SKIP] 08_segment_revenue - no segment data")

    if cds:
        try_chart(c09, "09_competitor_margin",    md, cds, out)
        try_chart(c10, "10_competitor_growth",    md, cds, out)
        try_chart(c11, "11_competitor_stability", md, cds, out)
        try_chart(c12, "12_competitor_cashflow",  md, cds, out)
    else:
        for n in ["09~12 경쟁사 차트"]:
            skipped.append(n)
        print("[SKIP] 09~12 - no competitor data")

    print(f"\n생성 완료: {len(gen)}개 | 스킵: {len(skipped)}개")


if __name__ == "__main__":
    main()
