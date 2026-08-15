#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const [manifestArg, outputArg] = process.argv.slice(2);
if (!manifestArg || !outputArg) {
  process.stderr.write("usage: reconstruct_pptx.cjs MANIFEST.json OUTPUT.pptx\n");
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(path.resolve(manifestArg), "utf8"));
const output = path.resolve(outputArg);
const slideW = 13.333;
const slideH = 7.5;
const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "ppt-gen";
pptx.subject = "OCR-assisted editable reconstruction";

for (const page of manifest.pages || []) {
  const slide = pptx.addSlide();
  const scale = Math.min(slideW / page.width, slideH / page.height);
  const w = page.width * scale;
  const h = page.height * scale;
  const ox = (slideW - w) / 2;
  const oy = (slideH - h) / 2;
  slide.background = { color: "FFFFFF" };
  slide.addImage({ path: page.image, x: ox, y: oy, w, h });
  for (const line of page.lines || []) {
    const x = ox + line.x * scale;
    const y = oy + line.y * scale;
    const boxW = Math.max(0.08, line.w * scale);
    const boxH = Math.max(0.08, line.h * scale);
    const fontSize = Math.max(6, Math.min(36, boxH * 72 * 0.72));
    slide.addText(line.text, { x, y, w: boxW, h: boxH, fontFace: "Aptos", fontSize, color: "111111", margin: 0, fit: "shrink", breakLine: false, fill: { color: line.fill || "FFFFFF", transparency: 4 }, line: { color: line.fill || "FFFFFF", transparency: 100 } });
  }
}
fs.mkdirSync(path.dirname(output), { recursive: true });
pptx.writeFile({ fileName: output }).catch((error) => { process.stderr.write(`error: ${error.message}\n`); process.exit(1); });
