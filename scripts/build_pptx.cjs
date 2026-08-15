#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");
const sizeOf = require("image-size");

const THEMES = {
  executive: { bg: "F7F7F4", ink: "18202A", muted: "65717C", accent: "D9483B", accent2: "2E6F73", surface: "FFFFFF", font: "Arial" },
  technical: { bg: "F4F7F8", ink: "13232C", muted: "5A6A72", accent: "00A39B", accent2: "F0A202", surface: "FFFFFF", font: "Arial" },
  academic: { bg: "FBFAF7", ink: "20252B", muted: "6B6F73", accent: "8B1E3F", accent2: "35605A", surface: "FFFFFF", font: "Arial" },
  editorial: { bg: "FCFBF8", ink: "151515", muted: "66625C", accent: "E4572E", accent2: "2F6690", surface: "FFFFFF", font: "Georgia" },
  midnight: { bg: "12181D", ink: "F4F5F6", muted: "A9B4BC", accent: "FFB703", accent2: "2EC4B6", surface: "1E2930", font: "Arial" },
  education: { bg: "FFFDF7", ink: "24313A", muted: "66747C", accent: "E85D75", accent2: "2A9D8F", surface: "FFFFFF", font: "Arial" },
};

function canvasFor(value) {
  const name = String(value || "16:9").toLowerCase();
  const known = { "16:9": [13.333, 7.5], "4:3": [10, 7.5], "16:10": [12, 7.5], "9:16": [4.219, 7.5], "a4-portrait": [8.267, 11.693], "a4-landscape": [11.693, 8.267] };
  if (known[name]) return { name, width: known[name][0], height: known[name][1] };
  const match = name.match(/^([0-9.]+)\s*[:x]\s*([0-9.]+)$/);
  if (!match) fail(`unsupported aspect ratio '${value}'`);
  const ratio = Number(match[1]) / Number(match[2]);
  return { name, width: 7.5 * ratio, height: 7.5 };
}

function scaleOptions(options, sx, sy) {
  const scaled = { ...(options || {}) };
  for (const key of ["x", "w"]) if (typeof scaled[key] === "number") scaled[key] *= sx;
  for (const key of ["y", "h"]) if (typeof scaled[key] === "number") scaled[key] *= sy;
  if (typeof scaled.fontSize === "number") scaled.fontSize *= Math.min(sx, sy);
  return scaled;
}

function makeResponsive(slide, sx, sy) {
  const addText = slide.addText.bind(slide);
  const addShape = slide.addShape.bind(slide);
  const addImage = slide.addImage.bind(slide);
  const addChart = slide.addChart.bind(slide);
  const addTable = slide.addTable.bind(slide);
  slide.addText = (text, options) => addText(text, scaleOptions(options, sx, sy));
  slide.addShape = (type, options) => addShape(type, scaleOptions(options, sx, sy));
  slide.addImage = (options) => addImage(scaleOptions(options, sx, sy));
  slide.addChart = (type, data, options) => addChart(type, data, scaleOptions(options, sx, sy));
  slide.addTable = (rows, options) => addTable(rows, scaleOptions(options, sx, sy));
  return slide;
}

function fail(message) {
  process.stderr.write(`error: ${message}\n`);
  process.exit(1);
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) { fail(`cannot read ${file}: ${error.message}`); }
}

function parseArgs(argv) {
  if (argv.length < 2) fail("usage: build_pptx.cjs PROJECT OUTPUT [--theme NAME]");
  const result = { project: path.resolve(argv[0]), output: path.resolve(argv[1]), theme: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--theme") result.theme = argv[++i];
    else fail(`unknown argument: ${argv[i]}`);
  }
  return result;
}

function fitText(text, limit) {
  const value = String(text || "").trim();
  if (value.length <= limit) return value;
  return value.slice(0, Math.max(1, limit - 1)).trimEnd() + "…";
}

function imageSizingContain(imagePath, x, y, w, h) {
  const dimensions = sizeOf(imagePath);
  const scale = Math.min(w / dimensions.width, h / dimensions.height);
  const shownW = dimensions.width * scale, shownH = dimensions.height * scale;
  return { path: imagePath, x: x + (w - shownW) / 2, y: y + (h - shownH) / 2, w: shownW, h: shownH };
}

function addSlideChrome(slide, pptx, theme, number, title, sourceIds) {
  slide.background = { color: theme.bg };
  slide.addShape(pptx.ShapeType.line, { x: 0.6, y: 0.42, w: 0.42, h: 0, line: { color: theme.accent, width: 3 } });
  slide.addText(fitText(title, 96), { x: 1.15, y: 0.2, w: 11.3, h: 0.66, fontFace: theme.font, fontSize: 35, bold: true, color: theme.ink, margin: 0, breakLine: false, fit: "shrink" });
  slide.addText(String(number).padStart(2, "0"), { x: 12.1, y: 7.08, w: 0.62, h: 0.2, fontFace: theme.font, fontSize: 8, color: theme.muted, align: "right", margin: 0 });
  if (sourceIds.length) {
    slide.addText(`Sources: ${sourceIds.join(", ")}`, { x: 0.65, y: 7.06, w: 8.8, h: 0.2, fontFace: theme.font, fontSize: 7.5, color: theme.muted, margin: 0, fit: "shrink" });
  }
}

function addBullets(slide, points, theme, box = {}) {
  const items = points.slice(0, 7).map((point) => ({
    text: fitText(typeof point === "string" ? point : point.text, 180),
    options: { bullet: { indent: 18 }, hanging: 4, breakLine: true },
  }));
  if (!items.length) return;
  slide.addText(items, {
    x: box.x ?? 0.85, y: box.y ?? 1.38, w: box.w ?? 5.4, h: box.h ?? 4.8,
    fontFace: theme.font, fontSize: box.fontSize ?? 19, color: theme.ink,
    breakLine: false, valign: "mid", margin: 0.08, paraSpaceAfterPt: 12, fit: "shrink",
  });
}

function resolveImage(project, value) {
  if (!value) return null;
  const candidate = typeof value === "string" ? value : value.path;
  if (!candidate) return null;
  const absolute = path.isAbsolute(candidate) ? candidate : path.resolve(project, candidate);
  return fs.existsSync(absolute) ? absolute : null;
}

function addImageOrStatement(slide, pptx, slideData, theme, project, reverse = false) {
  const panelX = reverse ? 0.85 : 6.85;
  const image = resolveImage(project, slideData.image);
  if (image) {
    slide.addShape(pptx.ShapeType.rect, { x: panelX - 0.1, y: 1.28, w: 5.8, h: 4.95, line: { color: theme.muted, transparency: 75 }, fill: { color: theme.surface } });
    slide.addImage(imageSizingContain(image, panelX, 1.38, 5.6, 4.75));
    return;
  }
  const statement = slideData.visual || slideData.key_message || slideData.action_title || "";
  slide.addShape(pptx.ShapeType.rect, { x: panelX, y: 1.55, w: 5.05, h: 3.7, line: { color: theme.accent, transparency: 100 }, fill: { color: theme.surface } });
  slide.addShape(pptx.ShapeType.rect, { x: panelX, y: 1.55, w: 0.1, h: 3.7, line: { color: theme.accent, transparency: 100 }, fill: { color: theme.accent } });
  slide.addText(fitText(statement, 140), { x: panelX + 0.4, y: 1.92, w: 4.2, h: 2.9, fontFace: theme.font, fontSize: 25, bold: true, color: theme.ink, valign: "mid", margin: 0, fit: "shrink" });
}

function addMetrics(slide, pptx, metrics, theme) {
  const values = metrics.slice(0, 4);
  const width = 11.8 / Math.max(1, values.length);
  values.forEach((metric, index) => {
    const x = 0.75 + index * width;
    slide.addText(fitText(metric.value ?? metric.number ?? "", 20), { x, y: 1.65, w: width - 0.28, h: 1.0, fontFace: theme.font, fontSize: 34, bold: true, color: index % 2 ? theme.accent2 : theme.accent, margin: 0, align: "center", fit: "shrink" });
    slide.addText(fitText(metric.label ?? metric.name ?? "", 55), { x, y: 2.75, w: width - 0.28, h: 0.55, fontFace: theme.font, fontSize: 16, color: theme.muted, margin: 0, align: "center", fit: "shrink" });
  });
}

function addChart(slide, pptx, chart, theme) {
  const kindMap = { bar: pptx.ChartType.bar, column: pptx.ChartType.bar, line: pptx.ChartType.line, pie: pptx.ChartType.pie, doughnut: pptx.ChartType.doughnut };
  const type = kindMap[String(chart.type || "bar").toLowerCase()] || pptx.ChartType.bar;
  const categories = chart.categories || [];
  const series = (chart.series || []).map((item, index) => ({ name: item.name || `Series ${index + 1}`, labels: categories, values: item.values || [] }));
  if (!series.length || !categories.length) return false;
  slide.addChart(type, series, {
    x: 0.85, y: 1.35, w: 7.7, h: 4.95,
    catAxisLabelFontFace: theme.font, catAxisLabelFontSize: 11,
    valAxisLabelFontFace: theme.font, valAxisLabelFontSize: 10,
    showLegend: series.length > 1, legendPos: "b", showTitle: false,
    chartColors: [theme.accent, theme.accent2, "758E9C", "E9C46A"],
    showValue: Boolean(chart.show_values), showCatName: false,
    showBorder: false,
  });
  if (chart.insight) {
    slide.addText(fitText(chart.insight, 160), { x: 9.05, y: 1.72, w: 3.25, h: 3.4, fontFace: theme.font, fontSize: 20, bold: true, color: theme.ink, margin: 0.05, valign: "mid", fit: "shrink" });
  }
  return true;
}

function addTable(slide, table, theme) {
  const headers = table.headers || [];
  const rows = (table.rows || []).slice(0, 10);
  if (!headers.length) return false;
  slide.addTable([headers, ...rows], {
    x: 0.75, y: 1.35, w: 11.85, h: 4.95,
    border: { type: "solid", color: "D9DEE2", pt: 0.8 },
    fill: theme.surface, color: theme.ink, fontFace: theme.font, fontSize: 16,
    margin: 0.08, breakLine: false,
    bold: false, rowH: 0.4,
  });
  return true;
}

function addComparison(slide, pptx, columns, points, theme) {
  const data = columns.length ? columns.slice(0, 3) : [
    { title: "Option A", points: points.filter((_, index) => index % 2 === 0) },
    { title: "Option B", points: points.filter((_, index) => index % 2 === 1) },
  ];
  const width = 11.65 / data.length;
  data.forEach((column, index) => {
    const x = 0.75 + index * width;
    slide.addShape(pptx.ShapeType.line, { x, y: 1.35, w: width - 0.32, h: 0, line: { color: index === 0 ? theme.accent : theme.accent2, width: 3 } });
    slide.addText(fitText(column.title || `Option ${index + 1}`, 42), { x, y: 1.56, w: width - 0.32, h: 0.55, fontFace: theme.font, fontSize: 20, bold: true, color: theme.ink, margin: 0, fit: "shrink" });
    addBullets(slide, column.points || column.supporting_points || [], theme, { x, y: 2.2, w: width - 0.32, h: 3.75, fontSize: 16 });
  });
}

function addProcess(slide, pptx, points, theme) {
  const steps = points.slice(0, 6);
  const width = 11.7 / Math.max(1, steps.length);
  steps.forEach((point, index) => {
    const x = 0.76 + index * width;
    if (index < steps.length - 1) slide.addShape(pptx.ShapeType.line, { x: x + width * 0.52, y: 2.38, w: width * 0.95, h: 0, line: { color: theme.muted, width: 1.2, beginArrowType: "none", endArrowType: "triangle" } });
    slide.addShape(pptx.ShapeType.ellipse, { x: x + width * 0.25, y: 1.85, w: 0.72, h: 0.72, line: { color: theme.accent, width: 2 }, fill: { color: theme.bg } });
    slide.addText(String(index + 1), { x: x + width * 0.25, y: 2.05, w: 0.72, h: 0.2, fontFace: theme.font, fontSize: 13, bold: true, color: theme.accent, align: "center", margin: 0 });
    slide.addText(fitText(typeof point === "string" ? point : point.text, 70), { x, y: 2.85, w: width - 0.15, h: 2.1, fontFace: theme.font, fontSize: 16, bold: true, color: theme.ink, align: "center", margin: 0.05, valign: "top", fit: "shrink" });
  });
}

function addDiagram(slide, pptx, diagram, theme) {
  const nodes = (diagram.nodes || []).slice(0, 7);
  if (!nodes.length) return false;
  const lookup = new Map();
  const width = 11.4 / nodes.length;
  nodes.forEach((node, index) => lookup.set(String(node.id ?? index), { x: 0.9 + index * width, y: 2.25, w: Math.min(1.65, width - 0.18), h: 1.05, node }));
  for (const edge of diagram.edges || []) {
    const from = lookup.get(String(edge.from)), to = lookup.get(String(edge.to));
    if (!from || !to) continue;
    slide.addShape(pptx.ShapeType.line, { x: from.x + from.w, y: from.y + from.h / 2, w: to.x - from.x - from.w, h: to.y - from.y, line: { color: theme.muted, width: 1.5, beginArrowType: "none", endArrowType: "triangle" } });
    if (edge.label) slide.addText(fitText(edge.label, 28), { x: from.x + from.w, y: from.y + 0.1, w: Math.max(0.5, to.x - from.x - from.w), h: 0.25, fontFace: theme.font, fontSize: 9, color: theme.muted, align: "center", margin: 0, fit: "shrink" });
  }
  for (const entry of lookup.values()) {
    slide.addShape(pptx.ShapeType.roundRect, { x: entry.x, y: entry.y, w: entry.w, h: entry.h, rectRadius: 0.04, line: { color: theme.accent, width: 1.5 }, fill: { color: theme.surface } });
    slide.addText(fitText(entry.node.label || entry.node.text || entry.node.id, 55), { x: entry.x + 0.08, y: entry.y + 0.12, w: entry.w - 0.16, h: entry.h - 0.24, fontFace: theme.font, fontSize: 15, bold: true, color: theme.ink, align: "center", valign: "mid", margin: 0.02, fit: "shrink" });
  }
  return true;
}

function addQuote(slide, pptx, data, theme) {
  const quote = data.quote || data.supporting_points?.[0] || data.visual || "";
  slide.addText(`“${fitText(quote, 260)}”`, { x: 1.25, y: 1.65, w: 10.8, h: 3.45, fontFace: theme.font, fontSize: 30, bold: true, italic: true, color: theme.ink, align: "center", valign: "mid", margin: 0.1, fit: "shrink" });
  if (data.attribution) slide.addText(fitText(data.attribution, 90), { x: 6.7, y: 5.35, w: 4.9, h: 0.45, fontFace: theme.font, fontSize: 16, color: theme.muted, align: "right", margin: 0, fit: "shrink" });
}

function addCover(slide, pptx, data, deck, theme) {
  slide.background = { color: theme.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.16, h: 7.5, line: { color: theme.accent, transparency: 100 }, fill: { color: theme.accent } });
  slide.addText(fitText(data.action_title || deck.title || "Presentation", 100), { x: 0.95, y: 1.35, w: 10.9, h: 2.2, fontFace: theme.font, fontSize: 50, bold: true, color: theme.ink, margin: 0, breakLine: false, fit: "shrink" });
  const subtitle = data.subtitle || deck.subtitle || deck.core_message || "";
  if (subtitle) slide.addText(fitText(subtitle, 160), { x: 0.98, y: 3.8, w: 8.8, h: 0.9, fontFace: theme.font, fontSize: 20, color: theme.muted, margin: 0, fit: "shrink" });
  const date = data.date || deck.date || "";
  if (date) slide.addText(date, { x: 0.98, y: 6.62, w: 3.2, h: 0.25, fontFace: theme.font, fontSize: 10, color: theme.muted, margin: 0 });
}

function addSection(slide, pptx, data, theme, number) {
  slide.background = { color: theme.accent };
  slide.addText(String(number).padStart(2, "0"), { x: 0.85, y: 0.82, w: 1.0, h: 0.55, fontFace: theme.font, fontSize: 22, bold: true, color: theme.bg, margin: 0 });
  slide.addText(fitText(data.action_title || "Section", 90), { x: 0.85, y: 2.1, w: 10.8, h: 1.6, fontFace: theme.font, fontSize: 39, bold: true, color: theme.bg, margin: 0, fit: "shrink" });
  if (data.supporting_points?.[0]) slide.addText(fitText(data.supporting_points[0], 140), { x: 0.88, y: 4.15, w: 8.8, h: 0.75, fontFace: theme.font, fontSize: 18, color: theme.bg, transparency: 10, margin: 0, fit: "shrink" });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const briefPath = path.join(args.project, "work", "brief.json");
  const storyboardPath = path.join(args.project, "work", "storyboard.json");
  if (!fs.existsSync(briefPath) || !fs.existsSync(storyboardPath)) fail("project must contain work/brief.json and work/storyboard.json");
  const brief = readJson(briefPath);
  const storyboard = readJson(storyboardPath);
  if (!Array.isArray(storyboard.slides) || storyboard.slides.length === 0) fail("storyboard.slides must contain at least one slide");
  const themeName = args.theme || brief.theme || "executive";
  const theme = THEMES[themeName];
  if (!theme) fail(`unknown theme '${themeName}'; choose ${Object.keys(THEMES).join(", ")}`);

  const pptx = new PptxGenJS();
  const canvas = canvasFor(brief.aspect_ratio || "16:9");
  pptx.defineLayout({ name: "PPT_GEN_CANVAS", width: canvas.width, height: canvas.height });
  pptx.layout = "PPT_GEN_CANVAS";
  pptx.author = brief.author || "ppt-gen";
  pptx.subject = brief.subject || brief.objective || "";
  pptx.title = brief.title || storyboard.deck?.title || "Presentation";
  pptx.company = brief.company || "";
  pptx.lang = brief.language || "en-US";
  pptx.theme = { headFontFace: theme.font, bodyFontFace: theme.font, lang: pptx.lang };

  storyboard.slides.forEach((data, index) => {
    const slide = makeResponsive(pptx.addSlide(), canvas.width / 13.333, canvas.height / 7.5);
    const role = String(data.role || "content").toLowerCase();
    const points = Array.isArray(data.supporting_points) ? data.supporting_points : [];
    const sources = Array.isArray(data.source_ids) ? data.source_ids : [];
    if (role === "cover") addCover(slide, pptx, data, storyboard.deck || {}, theme);
    else if (["section", "section_divider"].includes(role)) addSection(slide, pptx, data, theme, index + 1);
    else {
      addSlideChrome(slide, pptx, theme, index + 1, data.action_title || data.title || "", sources);
      if (data.diagram && addDiagram(slide, pptx, data.diagram, theme)) {
        // Diagram layout is complete.
      } else if (role === "quote") {
        addQuote(slide, pptx, data, theme);
      } else if (data.chart && addChart(slide, pptx, data.chart, theme)) {
        // Chart layout is complete.
      } else if (data.table && addTable(slide, data.table, theme)) {
        // Table layout is complete.
      } else if (Array.isArray(data.metrics) && data.metrics.length) {
        addMetrics(slide, pptx, data.metrics, theme);
        if (points.length) addBullets(slide, points, theme, { x: 1.15, y: 3.75, w: 10.8, h: 2.15, fontSize: 17 });
      } else if (role === "comparison") addComparison(slide, pptx, data.columns || [], points, theme);
      else if (role === "process") addProcess(slide, pptx, points, theme);
      else {
        const reverse = index % 2 === 0;
        addBullets(slide, points, theme, reverse ? { x: 6.95, y: 1.38, w: 5.35, h: 4.8 } : {});
        addImageOrStatement(slide, pptx, data, theme, args.project, reverse);
      }
    }
    const notes = [data.speaker_note || "", sources.length ? `[Sources]\n${sources.map((id) => `- ${id}`).join("\n")}` : ""].filter(Boolean).join("\n\n");
    if (notes) slide.addNotes(notes);
  });

  fs.mkdirSync(path.dirname(args.output), { recursive: true });
  await pptx.writeFile({ fileName: args.output });
  process.stdout.write(`Created ${args.output}\nSlides: ${storyboard.slides.length}\nTheme: ${themeName}\nAspect ratio: ${canvas.name}\n`);
}

main().catch((error) => fail(error.stack || error.message));
