// Build the project report .docx in the uGDX CPT 401 format.
//   node build.js                      -> ../DeepCrop_Project_Report.docx
// Page numbers in the contents lists come from pages.json, written by pagemap.py after a first build.

const fs = require('fs')
const path = require('path')
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, PageBreak, Footer, PageNumber, NumberFormat, ShadingType, LevelFormat, TabStopType,
  BorderStyle, VerticalAlign, ExternalHyperlink,
} = require('docx')
const { META, REFS, FRONT, CHAPTERS } = require('./content')

const FIG_DIR = path.join(__dirname, '..', 'figures')
const OUT = path.join(__dirname, '..', 'DeepCrop_Project_Report.docx')
const PAGES = fs.existsSync(path.join(__dirname, 'pages.json')) ? JSON.parse(fs.readFileSync(path.join(__dirname, 'pages.json'), 'utf8')) : {}

const FONT = 'Times New Roman'
const PAGE_W = 11906, MARGIN = 1440, TEXT_W = PAGE_W - 2 * MARGIN // A4, 1-inch margins
const BODY = { line: 360 } // 1.5 line spacing

// ---------- Citations: number by first use (IEEE) ----------
const order = []
const scan = (s) => (s.match(/\[@(\w+)\]/g) || []).forEach((m) => { const k = m.slice(2, -1); if (!order.includes(k)) order.push(k) })
for (const b of CHAPTERS) {
  if (b.text) scan(b.text)
  if (b.items) b.items.forEach(scan)
  if (b.rows) b.rows.flat().forEach(scan)
}
const missing = order.filter((k) => !REFS[k])
if (missing.length) throw new Error('Missing references: ' + missing.join(', '))
const cite = (s) => s.replace(/\[@(\w+)\]/g, (_, k) => `[${order.indexOf(k) + 1}]`)

// ---------- Text runs with {{placeholder}} highlighting ----------
function runs(text, opts = {}) {
  return cite(text).split(/(\{\{[^}]+\}\})/).filter(Boolean).map((part) =>
    part.startsWith('{{')
      ? new TextRun({ text: part.slice(2, -2), font: FONT, highlight: 'yellow', ...opts })
      : new TextRun({ text: part, font: FONT, ...opts }))
}

const para = (text, o = {}) => new Paragraph({
  children: runs(text, o.run || {}), alignment: o.align ?? AlignmentType.JUSTIFIED,
  spacing: { ...BODY, before: o.before ?? 0, after: o.after ?? 120 }, ...(o.extra || {}),
})

// ---------- Numbering for captions ----------
let chapter = 0, figN = 0, tabN = 0
const figures = [], tables = [], toc = []

function pngSize(file) {
  const b = fs.readFileSync(file)
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b }
}

function figure(b) {
  figN += 1
  const label = `Figure ${chapter}.${figN}: ${b.caption}`
  figures.push(label)
  const file = path.join(FIG_DIR, b.src)
  const { w, h, data } = pngSize(file)
  const widthPx = Math.round((b.width / 2.54) * 96)
  const heightPx = Math.round(widthPx * h / w)
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: 'png', data, transformation: { width: widthPx, height: heightPx } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: runs(label, { size: 22 }) }),
  ]
}

function table(b) {
  tabN += 1
  const label = `Table ${chapter}.${tabN}: ${b.caption}`
  tables.push(label)
  const widths = b.widths.map((p) => Math.round(TEXT_W * p / 100))
  widths[widths.length - 1] = TEXT_W - widths.slice(0, -1).reduce((a, c) => a + c, 0)
  const border = { style: BorderStyle.SINGLE, size: 4, color: '808080' }
  const cell = (text, i, header) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: header ? { type: ShadingType.CLEAR, fill: 'E7E9E4', color: 'auto' } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: 260 },
      children: runs(text, { size: 21, bold: !!header }) })],
  })
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 80 }, children: runs(label, { size: 22 }) }),
    new Table({
      width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths,
      rows: [
        new TableRow({ tableHeader: true, children: b.header.map((t, i) => cell(t, i, true)) }),
        ...b.rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) })),
      ],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ]
}

let listInstance = 0
function list(b, ref) {
  listInstance += 1
  const inst = listInstance
  return b.items.map((item) => new Paragraph({
    numbering: { reference: ref, level: 0, instance: inst }, alignment: AlignmentType.JUSTIFIED,
    spacing: { ...BODY, after: 80 }, children: runs(item),
  }))
}

function heading(b) {
  if (b.t === 'h1') {
    chapter += 1; figN = 0; tabN = 0
    toc.push({ text: b.text, level: 0 })
    return [new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: runs(b.text) })]
  }
  toc.push({ text: b.text, level: b.t === 'h2' ? 1 : 2 })
  return [new Paragraph({ heading: b.t === 'h2' ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3, children: runs(b.text) })]
}

const body = []
for (const b of CHAPTERS) {
  if (b.t.startsWith('h')) body.push(...heading(b))
  else if (b.t === 'p') body.push(para(b.text))
  else if (b.t === 'bullets') body.push(...list(b, 'bullets'))
  else if (b.t === 'numbered') body.push(...list(b, 'numbers'))
  else if (b.t === 'fig') body.push(...figure(b))
  else if (b.t === 'table') body.push(...table(b))
  else if (b.t === 'eq') body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 },
    children: [new TextRun({ text: b.text, font: 'Cambria Math', italics: true, size: 24 })] }))
}

// References chapter
toc.push({ text: 'References', level: 0 })
body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: runs('References') }))
order.forEach((k, i) => body.push(new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { line: 300, after: 100 }, indent: { left: 567, hanging: 567 },
  children: [new TextRun({ text: `[${i + 1}]\t`, font: FONT }), ...runs(REFS[k])],
})))

// ---------- Front matter ----------
const center = (text, size, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, before: o.before ?? 0 },
  children: runs(text, { size, bold: !!o.bold, italics: !!o.italics }) })
const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [] }))
const studentLine = ([name, id]) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [...runs(name, { size: 26 }), new TextRun({ text: '\t\t', font: FONT }), ...runs(id, { size: 26 })] })

const titlePage = [
  ...blank(1), center('uGDX School of Technology', 36, { bold: true, after: 480 }),
  center('Project Report on', 28, { after: 200 }),
  center(`“${META.title}”`, 32, { bold: true, after: 480 }),
  center('Submitted in partial fulfillment of the requirements', 24, { after: 40 }),
  center('for the course', 24, { after: 240 }),
  center('Course: Design Project Minor (CPT 401)', 24, { bold: true, after: 40 }),
  center('Class: Final Year B. Tech (Semester VII)', 24, { bold: true, after: 400 }),
  center('By', 24, { italics: true, after: 200 }),
  ...META.students.map(studentLine),
  ...blank(1),
  center('Supervisor:', 24, { bold: true, before: 240, after: 40 }),
  center(META.supervisor, 26, { after: 40 }),
  center(`(${META.affiliation})`, 24, { after: 280 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 280 }, children: [
    new TextRun({ text: 'Project code: ', font: FONT, size: 24, bold: true }),
    new ExternalHyperlink({ link: META.repo, children: [new TextRun({ text: META.repo, font: FONT, size: 24, style: 'Hyperlink' })] }),
  ] }),
  center(`AY: ${META.year}`, 26, { bold: true }),
]

const certificatePage = [
  new Paragraph({ children: [new PageBreak()] }),
  ...blank(1), center('uGDX School of Technology', 36, { bold: true, after: 600 }),
  center('CERTIFICATE', 32, { bold: true, after: 600 }),
  para(`This is to certify that the project entitled “${META.title}” is a bonafide work of`, { after: 240 }),
  ...META.students.map(studentLine),
  para('submitted in partial fulfilment of the requirement for the course “Design Project Minor” of Final Year of Bachelor degree in Technology (CS, AI & ML) during academic year 2026-27.', { before: 240 }),
  ...blank(5),
  new Paragraph({ tabStops: [{ type: 'right', position: TEXT_W }], children: [...runs('Supervisor/Guide', { bold: true }), new TextRun({ text: '\tExaminer', font: FONT, bold: true })] }),
  new Paragraph({ children: runs(`(${META.supervisor})`) }),
]

const frontHeading = (text, pageBreak = true) => new Paragraph({ alignment: AlignmentType.CENTER, pageBreakBefore: pageBreak,
  spacing: { after: 240 }, children: runs(text, { size: 32, bold: true }) })

// Right tab stop with a dot leader at the margin: renders the same in Word and LibreOffice
const dotLine = (text, page, indent = 0, bold = false) => new Paragraph({
  indent: { left: indent }, spacing: { line: 264, after: 30 },
  tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: 'dot' }],
  children: [...runs(text, { bold }), new TextRun({ text: `\t${page ?? '–'}`, font: FONT, bold })],
})

const twoCol = (rows) => new Table({
  width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [2200, TEXT_W - 2200],
  borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE },
    right: { style: BorderStyle.NONE }, insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE } },
  rows: rows.map(([a, b]) => new TableRow({ children: [
    new TableCell({ width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ spacing: { after: 60 }, children: runs(a, { bold: true }) })] }),
    new TableCell({ width: { size: TEXT_W - 2200, type: WidthType.DXA }, children: [new Paragraph({ spacing: { after: 60 }, children: runs(b) })] }),
  ] })),
})

const front = [
  frontHeading('Acknowledgement', false), ...FRONT.acknowledgement.map((t) => para(t)),
  ...blank(2), new Paragraph({ alignment: AlignmentType.RIGHT, children: runs('Manav Arora') }),
  frontHeading('Abstract'), ...FRONT.abstract.map((t, i) => para(t, i === FRONT.abstract.length - 1 ? { run: { italics: true } } : {})),
  frontHeading('Table of Contents'),
  ...toc.map((e) => dotLine(e.text, PAGES[e.text], e.level * 400, e.level === 0)),
  frontHeading('List of Figures'), ...figures.map((f) => dotLine(f, PAGES[f])),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 360, after: 240 }, children: runs('List of Tables', { size: 32, bold: true }) }),
  ...tables.map((t) => dotLine(t, PAGES[t])),
  frontHeading('Abbreviations, Notation and Nomenclature'),
  new Paragraph({ spacing: { after: 120 }, children: runs('Abbreviations', { size: 28, bold: true }) }), twoCol(FRONT.abbreviations),
  new Paragraph({ spacing: { before: 240, after: 120 }, children: runs('Notation', { size: 28, bold: true }) }), twoCol(FRONT.notation),
]

const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 22 })] })] })
const pageProps = (fmt, start) => ({ page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
  pageNumbers: { start, formatType: fmt } } })

const doc = new Document({
  creator: 'DeepCrop project team',
  title: META.title,
  styles: {
    default: { document: { run: { font: FONT, size: 24 }, paragraph: { spacing: BODY } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: '000000' }, paragraph: { spacing: { before: 0, after: 240 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: '000000' }, paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: '000000' }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567, hanging: 283 } } } }] },
    { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567, hanging: 340 } } } }] },
  ] },
  sections: [
    { properties: pageProps(NumberFormat.LOWER_ROMAN, 1), children: [...titlePage, ...certificatePage] },
    { properties: pageProps(NumberFormat.LOWER_ROMAN, 1), footers: { default: footer }, children: front },
    { properties: pageProps(NumberFormat.DECIMAL, 1), footers: { default: footer }, children: body },
  ],
})

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf)
  fs.writeFileSync(path.join(__dirname, 'entries.json'), JSON.stringify({ toc: toc.map((e) => e.text), figures, tables }, null, 2))
  console.log(`Wrote ${OUT}: ${figures.length} figures, ${tables.length} tables, ${order.length} references`)
})
