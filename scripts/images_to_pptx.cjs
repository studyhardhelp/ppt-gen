#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");
const sizeOf = require("image-size");

function fail(message) { process.stderr.write(`error: ${message}\n`); process.exit(1); }
function canvasFor(value) {
  const name = String(value || "16:9").toLowerCase();
  const known = { "16:9": [13.333, 7.5], "4:3": [10, 7.5], "16:10": [12, 7.5], "9:16": [4.219, 7.5], "a4-portrait": [8.267, 11.693], "a4-landscape": [11.693, 8.267] };
  if (known[name]) return { name, width: known[name][0], height: known[name][1] };
  const match = name.match(/^([0-9.]+)\s*[:x]\s*([0-9.]+)$/);
  if (!match) fail(`unsupported aspect ratio: ${value}`);
  return { name, width: 7.5 * Number(match[1]) / Number(match[2]), height: 7.5 };
}
function parseArgs(values) {
  if (values.length < 2) fail("usage: images_to_pptx.cjs IMAGE_DIR OUTPUT.pptx [--manifest FILE] [--aspect-ratio RATIO]");
  const result = { input: path.resolve(values[0]), output: path.resolve(values[1]), manifest: null, aspect: "16:9" };
  for (let index = 2; index < values.length; index += 1) {
    if (values[index] === "--manifest") result.manifest = path.resolve(values[++index]);
    else if (values[index] === "--aspect-ratio") result.aspect = values[++index];
    else fail(`unknown argument: ${values[index]}`);
  }
  return result;
}
function contained(image, canvas) {
  const dimensions = sizeOf(image);
  const scale = Math.min(canvas.width / dimensions.width, canvas.height / dimensions.height);
  const w = dimensions.width * scale, h = dimensions.height * scale;
  return { x: (canvas.width - w) / 2, y: (canvas.height - h) / 2, w, h };
}

const options = parseArgs(process.argv.slice(2));
const extensions = new Set([".png", ".jpg", ".jpeg", ".webp"]);
let entries;
if (options.manifest) {
  const data = JSON.parse(fs.readFileSync(options.manifest, "utf8"));
  const base = path.dirname(options.manifest);
  entries = (data.slides || data).map((item) => ({ ...item, path: path.isAbsolute(item.path) ? item.path : path.resolve(base, item.path) }));
  if (data.aspect_ratio) options.aspect = data.aspect_ratio;
} else {
  entries = fs.readdirSync(options.input)
    .filter((name) => extensions.has(path.extname(name).toLowerCase()) && !name.startsWith("contact-sheet") && !name.startsWith("diff-"))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((name) => ({ path: path.join(options.input, name), alt: name, notes: "", sources: [] }));
}
if (!entries.length) fail(`no slide images found in ${options.input}`);
for (const entry of entries) if (!fs.existsSync(entry.path)) fail(`missing image: ${entry.path}`);

const canvas = canvasFor(options.aspect);
const pptx = new PptxGenJS();
pptx.defineLayout({ name: "PPT_GEN_IMAGES", width: canvas.width, height: canvas.height });
pptx.layout = "PPT_GEN_IMAGES";
pptx.author = "ppt-gen";
pptx.subject = "Image-first presentation";
for (const entry of entries) {
  const slide = pptx.addSlide();
  slide.background = { color: entry.background || "000000" };
  slide.addImage({ path: entry.path, ...contained(entry.path, canvas), altText: entry.alt || path.basename(entry.path) });
  const sources = Array.isArray(entry.sources) && entry.sources.length ? `[Sources]\n${entry.sources.map((source) => `- ${source}`).join("\n")}` : "";
  const notes = [entry.notes || "", sources].filter(Boolean).join("\n\n");
  if (notes) slide.addNotes(notes);
}
fs.mkdirSync(path.dirname(options.output), { recursive: true });
pptx.writeFile({ fileName: options.output })
  .then(() => process.stdout.write(`Created ${options.output}\nSlides: ${entries.length}\nAspect ratio: ${canvas.name}\nEditability: slide images only\n`))
  .catch((error) => fail(error.message));
