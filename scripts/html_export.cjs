#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

function args(values) {
  if (values.length < 3) throw new Error("usage: html_export.cjs INPUT.html pdf|images OUTPUT");
  return { input: path.resolve(values[0]), mode: values[1], output: path.resolve(values[2]) };
}
function browserPath() {
  const candidates = [process.env.CHROME_PATH, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Chromium.app/Contents/MacOS/Chromium"].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

(async () => {
  const options = args(process.argv.slice(2));
  const executablePath = browserPath();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: options.mode === "images" ? 2 : 1 });
  await page.goto(pathToFileURL(options.input).href, { waitUntil: "networkidle" });
  const size = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return { width: parseInt(style.getPropertyValue("--stage-w"), 10) || 1280, height: parseInt(style.getPropertyValue("--stage-h"), 10) || 720, slides: document.querySelectorAll(".slide").length };
  });
  await page.setViewportSize({ width: size.width, height: size.height });
  if (options.mode === "pdf") {
    fs.mkdirSync(path.dirname(options.output), { recursive: true });
    await page.pdf({ path: options.output, width: `${size.width}px`, height: `${size.height}px`, printBackground: true, preferCSSPageSize: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  } else if (options.mode === "images") {
    fs.mkdirSync(options.output, { recursive: true });
    for (let index = 0; index < size.slides; index += 1) {
      await page.evaluate((n) => window.show(n), index);
      await page.locator(".slide.active").screenshot({ path: path.join(options.output, `slide-${String(index + 1).padStart(2, "0")}.png`) });
    }
  } else throw new Error(`unsupported mode: ${options.mode}`);
  await browser.close();
  process.stdout.write(`Created ${options.output}\nSlides: ${size.slides}\n`);
})().catch((error) => { process.stderr.write(`error: ${error.stack || error.message}\n`); process.exit(1); });
