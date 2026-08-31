/**
 * Markdown → Word(.docx) 변환.
 * 사용: node generate_docx.js <input.md> <output.docx>
 * 의존: docx@8, marked@12
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, WidthType, ShadingType,
  BorderStyle, TableLayoutType,
} = require("docx");
const { marked } = require("marked");

// ─── 색상 상수 ──────────────────────────────────────────
const COLOR = {
  HEADING1: "1F3864",
  HEADING2: "2F5496",
  TABLE_HEADER_BG: "2F5496",
  TABLE_HEADER_FG: "FFFFFF",
  TABLE_ROW_ALT: "EEF2F8",
  TABLE_ROW_NORMAL: "FFFFFF",
  POSITIVE: "1E8449",
  NEGATIVE: "C0392B",
  BORDER: "AAAAAA",
};

// ─── 헬퍼 ───────────────────────────────────────────────
function colorOfUpside(text) {
  if (!text || text === "N/A") return null;
  if (text.includes("▲") || text.startsWith("+")) return COLOR.POSITIVE;
  if (text.includes("▼") || text.startsWith("-")) return COLOR.NEGATIVE;
  return null;
}

function makeRun(text, opts = {}) {
  return new TextRun({
    text: text || "",
    bold: opts.bold || false,
    color: opts.color || undefined,
    size: opts.size || 22,
    font: "맑은 고딕",
  });
}

function makeHeading(text, level) {
  const colorMap = { 1: COLOR.HEADING1, 2: COLOR.HEADING2 };
  const sizeMap = { 1: 36, 2: 28, 3: 24 };
  const headingMap = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({
    heading: headingMap[level] || HeadingLevel.HEADING_3,
    children: [
      new TextRun({
        text,
        bold: true,
        color: colorMap[level] || "000000",
        size: sizeMap[level] || 22,
        font: "맑은 고딕",
      }),
    ],
    spacing: { before: 240, after: 120 },
  });
}

function makeParagraph(text) {
  return new Paragraph({
    children: [makeRun(text)],
    spacing: { after: 80 },
  });
}

function makeTableRow(cells, isHeader = false, isAlt = false) {
  const bg = isHeader ? COLOR.TABLE_HEADER_BG : (isAlt ? COLOR.TABLE_ROW_ALT : COLOR.TABLE_ROW_NORMAL);
  const fg = isHeader ? COLOR.TABLE_HEADER_FG : "000000";

  return new TableRow({
    children: cells.map((cell) => {
      const upColor = !isHeader ? colorOfUpside(String(cell)) : null;
      return new TableCell({
        children: [
          new Paragraph({
            children: [
              new TextRun({
                text: String(cell),
                bold: isHeader,
                color: upColor || fg,
                size: 20,
                font: "맑은 고딕",
              }),
            ],
            alignment: AlignmentType.CENTER,
          }),
        ],
        shading: { type: ShadingType.CLEAR, fill: bg },
        margins: { top: 60, bottom: 60, left: 80, right: 80 },
      });
    }),
  });
}

function makeTable(rows) {
  if (!rows || rows.length < 2) return null;
  const docRows = [];
  rows.forEach((row, i) => {
    if (i === 0) docRows.push(makeTableRow(row, true));
    else if (i === 1 && row.every((c) => /^[-|: ]+$/.test(c))) return;
    else docRows.push(makeTableRow(row, false, i % 2 === 0));
  });

  return new Table({
    rows: docRows,
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
  });
}

// ─── Markdown 파서 ───────────────────────────────────────
function parseMarkdown(md) {
  const elements = [];
  const lines = md.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 수평선
    if (/^---+$/.test(line.trim())) {
      elements.push(new Paragraph({ text: "", spacing: { after: 240 } }));
      i++;
      continue;
    }

    // 제목
    const h1 = line.match(/^# (.+)/);
    const h2 = line.match(/^## (.+)/);
    const h3 = line.match(/^### (.+)/);
    if (h1) { elements.push(makeHeading(h1[1], 1)); i++; continue; }
    if (h2) { elements.push(makeHeading(h2[1], 2)); i++; continue; }
    if (h3) { elements.push(makeHeading(h3[1], 3)); i++; continue; }

    // 표 감지
    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = tableLines.map((l) =>
        l.split("|").slice(1, -1).map((c) => c.trim())
      );
      const tbl = makeTable(rows);
      if (tbl) elements.push(tbl);
      elements.push(new Paragraph({ text: "", spacing: { after: 120 } }));
      continue;
    }

    // 인용문
    const blockquote = line.match(/^> (.+)/);
    if (blockquote) {
      elements.push(
        new Paragraph({
          children: [makeRun(blockquote[1], { color: "555555" })],
          indent: { left: 480 },
          spacing: { after: 80 },
        })
      );
      i++;
      continue;
    }

    // 목록
    const bullet = line.match(/^[-*] (.+)/);
    if (bullet) {
      elements.push(
        new Paragraph({
          children: [makeRun(`• ${bullet[1]}`)],
          indent: { left: 360 },
          spacing: { after: 60 },
        })
      );
      i++;
      continue;
    }

    // 빈 줄
    if (line.trim() === "") {
      elements.push(new Paragraph({ text: "", spacing: { after: 60 } }));
      i++;
      continue;
    }

    // 일반 텍스트 (볼드 처리)
    const parts = line.split(/\*\*([^*]+)\*\*/);
    const runs = parts.map((p, idx) =>
      makeRun(p, { bold: idx % 2 === 1 })
    );
    elements.push(new Paragraph({ children: runs, spacing: { after: 80 } }));
    i++;
  }

  return elements;
}

// ─── 메인 ───────────────────────────────────────────────
async function main() {
  const [,, inputMd, outputDocx] = process.argv;
  if (!inputMd || !outputDocx) {
    console.error("사용법: node generate_docx.js <input.md> <output.docx>");
    process.exit(1);
  }

  if (!fs.existsSync(inputMd)) {
    console.error(`[ERROR] 입력 파일 없음: ${inputMd}`);
    process.exit(1);
  }

  const md = fs.readFileSync(inputMd, "utf-8");
  const children = parseMarkdown(md);

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
          },
        },
        children,
      },
    ],
    styles: {
      default: {
        document: {
          run: { font: "맑은 고딕", size: 22 },
        },
      },
    },
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputDocx, buffer);
  console.log(`[OK] Word 문서 저장: ${outputDocx}`);
}

main().catch((e) => {
  console.error(`[ERROR] docx 생성 실패: ${e.message}`);
  process.exit(1);
});
