#!/usr/bin/env node
/**
 * generate_report_docx.js — 분석 리포트 Word 문서 생성 (docx npm)
 *
 * Usage:
 *   node generate_report_docx.js \
 *     --analysis analysis.txt \
 *     --financials financials.json \
 *     --charts-dir charts/ \
 *     --output report.docx
 *
 * 의존성: npm install docx
 */

const fs   = require("fs");
const path = require("path");

let docxLib;
try {
  docxLib = require("docx");
} catch {
  console.error("[ERROR] docx 패키지 미설치 — npm install docx 실행 후 재시도");
  process.exit(1);
}

const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  ImageRun, PageBreak, AlignmentType,
} = docxLib;

function parseArgs() {
  const args = process.argv.slice(2);
  const r = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) { r[args[i].slice(2)] = args[i + 1]; i++; }
  }
  return r;
}

function txt(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, size: 22, ...opts })] });
}

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ text, heading: level });
}

function chartParagraph(imgPath) {
  if (!fs.existsSync(imgPath)) {
    return new Paragraph({
      children: [new TextRun({
        text: `[차트 미생성: ${path.basename(imgPath)}]`,
        color: "999999", italics: true, size: 20,
      })],
    });
  }
  return new Paragraph({
    children: [new ImageRun({
      data: fs.readFileSync(imgPath),
      transformation: { width: 550, height: 275 },
      type: "png",
    })],
    alignment: AlignmentType.CENTER,
  });
}

function parseAnalysisToBlocks(text) {
  return text.split("\n").map(line => {
    if (line.startsWith("# "))   return heading(line.slice(2), HeadingLevel.HEADING_1);
    if (line.startsWith("## "))  return heading(line.slice(3), HeadingLevel.HEADING_2);
    if (line.startsWith("### ")) return heading(line.slice(4), HeadingLevel.HEADING_3);
    return txt(line);
  });
}

async function main() {
  const args = parseArgs();
  if (!args.analysis || !args.financials || !args.output) {
    console.error("필수 인자 누락: --analysis --financials --output");
    process.exit(1);
  }

  const analysis  = fs.readFileSync(args.analysis,   "utf-8");
  const fin       = JSON.parse(fs.readFileSync(args.financials, "utf-8"));
  const chartsDir = args["charts-dir"] || "charts";

  const company   = fin.company?.name || "";
  const rtype     = fin.company?.report_type || "연결";
  const dr        = fin.data_range || {};
  const dateStr   = new Date().toLocaleDateString("ko-KR",
    { year: "numeric", month: "long", day: "numeric" });

  function cp(filename) { return path.join(chartsDir, filename); }

  const children = [
    // 표지
    new Paragraph({
      children: [new TextRun({ text: company, bold: true, size: 52 })],
      alignment: AlignmentType.CENTER,
      spacing: { before: 1800, after: 400 },
    }),
    new Paragraph({
      children: [new TextRun({ text: "재무실적 분석 리포트", size: 36 })],
      alignment: AlignmentType.CENTER, spacing: { after: 240 },
    }),
    txt(`분석일자: ${dateStr}`, { size: 22 }),
    txt(`분석 기간: ${dr.start_year || ""}–${dr.end_year || ""}년  |  기준: ${rtype}`, { size: 22 }),
    new Paragraph({ children: [new PageBreak()] }),

    // 분석 본문
    ...parseAnalysisToBlocks(analysis),
    new Paragraph({ children: [new PageBreak()] }),

    // 차트 섹션
    heading("차트 첨부"),
    heading("수익성 분석", HeadingLevel.HEADING_2),
    chartParagraph(cp("01_revenue_profit_trend.png")),
    chartParagraph(cp("02_margin_trend.png")),
    chartParagraph(cp("03_roe_roa_trend.png")),
    heading("안정성 분석", HeadingLevel.HEADING_2),
    chartParagraph(cp("04_debt_stability.png")),
    heading("성장성 분석", HeadingLevel.HEADING_2),
    chartParagraph(cp("07_growth_rate.png")),
    heading("현금흐름 분석", HeadingLevel.HEADING_2),
    chartParagraph(cp("05_cashflow_breakdown.png")),
    chartParagraph(cp("06_fcf_trend.png")),
  ];

  // 세그먼트 차트
  if (fs.existsSync(cp("08_segment_revenue.png"))) {
    children.push(heading("수익구조 분석", HeadingLevel.HEADING_2));
    children.push(chartParagraph(cp("08_segment_revenue.png")));
  }

  // 경쟁사 차트
  const compFiles = ["09_competitor_margin.png","10_competitor_growth.png",
                     "11_competitor_stability.png","12_competitor_cashflow.png"];
  if (compFiles.some(f => fs.existsSync(cp(f)))) {
    children.push(heading("경쟁사 비교 분석", HeadingLevel.HEADING_2));
    compFiles.forEach(f => children.push(chartParagraph(cp(f))));
  }

  const doc = new Document({
    creator: "Financial Analysis Agent",
    title:   `${company} 재무실적 분석 리포트`,
    sections: [{ properties: {}, children }],
  });

  const buf = await Packer.toBuffer(doc);
  const outPath = args.output;
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log(`[OK] report.docx 저장: ${outPath}`);
}

main().catch(e => { console.error(e); process.exit(1); });
