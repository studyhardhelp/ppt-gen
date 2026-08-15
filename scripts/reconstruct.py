#!/usr/bin/env python3
"""Reconstruct PDF or slide images into an editable, OCR-assisted PPTX."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from doctor import build_report


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result


def source_images(source: Path, workspace: Path) -> list[Path]:
    if source.is_dir():
        return sorted((path for path in source.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES), key=lambda path: path.name)
    if source.suffix.lower() in IMAGE_SUFFIXES:
        return [source]
    if source.suffix.lower() == ".pdf":
        render = Path(__file__).resolve().parent / "render_deck.py"
        run([sys.executable, str(render), str(source), "--output-dir", str(workspace), "--clean"])
        return sorted(workspace.glob("slide-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    raise ValueError("Reconstruction accepts PDF, PNG, JPG, or an image directory")


def sample_fill(image, box: tuple[int, int, int, int]) -> str:
    from PIL import ImageStat

    x, y, w, h = box
    pad = max(2, int(min(w, h) * 0.08))
    left, top = max(0, x - pad), max(0, y - pad)
    right, bottom = min(image.width, x + w + pad), min(image.height, y + h + pad)
    region = image.crop((left, top, right, bottom)).convert("RGB")
    median = ImageStat.Stat(region).median
    return "".join(f"{int(value):02X}" for value in median[:3])


def ocr_page(image_path: Path, tesseract: str, language: str) -> dict:
    from PIL import Image

    image = Image.open(image_path)
    result = run([tesseract, str(image_path), "stdout", "-l", language, "tsv"])
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in csv.DictReader(result.stdout.splitlines(), delimiter="\t"):
        text = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1
        if text and confidence >= 55:
            groups[(row["block_num"], row["par_num"], row["line_num"])].append(row)
    lines = []
    for words in groups.values():
        left = min(int(word["left"]) for word in words)
        top = min(int(word["top"]) for word in words)
        right = max(int(word["left"]) + int(word["width"]) for word in words)
        bottom = max(int(word["top"]) + int(word["height"]) for word in words)
        box = (left, top, right - left, bottom - top)
        lines.append({"text": " ".join(word["text"] for word in words), "x": left, "y": top, "w": right - left, "h": bottom - top, "fill": sample_fill(image, box)})
    return {"image": str(image_path), "width": image.width, "height": image.height, "lines": sorted(lines, key=lambda line: (line["y"], line["x"]))}


def ocr_page_vision(image_path: Path, swift: str, language: str) -> dict:
    from PIL import Image

    image = Image.open(image_path)
    script = Path(__file__).resolve().parent / "macos_vision_ocr.swift"
    result = run([swift, str(script), str(image_path), language], timeout=120)
    raw_lines = json.loads(result.stdout)
    lines = []
    for item in raw_lines:
        if item.get("text", "").strip() and float(item.get("confidence", 0)) >= 0.35:
            box = (int(item["x"]), int(item["y"]), int(item["w"]), int(item["h"]))
            lines.append({"text": item["text"].strip(), "x": box[0], "y": box[1], "w": box[2], "h": box[3], "fill": sample_fill(image, box)})
    return {"image": str(image_path), "width": image.width, "height": image.height, "lines": sorted(lines, key=lambda line: (line["y"], line["x"]))}


def reconstruct(source: Path, output: Path, language: str, aspect_ratio: str) -> None:
    report = build_report()
    tools = report["tools"]
    if not report["capabilities"]["native_pptx_generation"]:
        raise RuntimeError("PptxGenJS is required for reconstruction")
    if not report["capabilities"].get("ocr_reconstruction"):
        raise RuntimeError("Tesseract or macOS Vision OCR is required for editable reconstruction")
    if not tools.get("pillow"):
        raise RuntimeError("Pillow is required for editable reconstruction")
    with tempfile.TemporaryDirectory(prefix="ppt-gen-reconstruct-") as directory:
        workspace = Path(directory)
        images = source_images(source, workspace)
        if not images:
            raise RuntimeError("No source pages were found")
        if tools.get("tesseract"):
            provider = "tesseract"
            pages = [ocr_page(image, tools["tesseract"], language) for image in images]
        else:
            provider = "macos-vision"
            pages = [ocr_page_vision(image, tools["swift"], language) for image in images]
        manifest = {"schema": "ppt-reconstruction/v1", "provider": provider, "pages": pages}
        manifest_path = workspace / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        env = os.environ.copy()
        if tools.get("node_path"):
            env["NODE_PATH"] = tools["node_path"]
        run([tools["node"], str(Path(__file__).resolve().parent / "reconstruct_pptx.cjs"), str(manifest_path), str(output), "--aspect-ratio", aspect_ratio], env=env)
    print(f"Created {output}\nPages: {len(images)}\nOCR: {provider}\nMode: image fidelity plus editable OCR text overlays")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", default="eng", help="Tesseract language code, for example eng or chi_sim+eng")
    parser.add_argument("--aspect-ratio", default="16:9")
    args = parser.parse_args()
    try:
        reconstruct(args.source.resolve(), args.output.resolve(), args.language, args.aspect_ratio)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
