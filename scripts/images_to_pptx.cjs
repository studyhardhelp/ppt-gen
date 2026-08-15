#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const [inputArg, outputArg] = process.argv.slice(2);
if (!inputArg || !outputArg) {
  process.stderr.write("usage: images_to_pptx.cjs IMAGE_DIR OUTPUT.pptx\n");
  process.exit(1);
}
const input = path.resolve(inputArg);
const output = path.resolve(outputArg);
const extensions = new Set([".png", ".jpg", ".jpeg"]);
const images = fs.readdirSync(input)
  .filter((name) => extensions.has(path.extname(name).toLowerCase()) && !name.startsWith("contact-sheet") && !name.startsWith("diff-"))
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
if (!images.length) {
  process.stderr.write(`error: no PNG/JPG images found in ${input}\n`);
  process.exit(1);
}

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "ppt-gen";
pptx.subject = "Image-first presentation";
for (const name of images) {
  const slide = pptx.addSlide();
  slide.background = { color: "000000" };
  slide.addImage({ path: path.join(input, name), x: 0, y: 0, w: 13.333, h: 7.5, sizing: "contain" });
}
fs.mkdirSync(path.dirname(output), { recursive: true });
pptx.writeFile({ fileName: output })
  .then(() => process.stdout.write(`Created ${output}\nSlides: ${images.length}\nEditability: slide images only\n`))
  .catch((error) => { process.stderr.write(`error: ${error.message}\n`); process.exit(1); });
