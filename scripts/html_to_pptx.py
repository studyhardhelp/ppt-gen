#!/usr/bin/env python3
"""Render an HTML deck and assemble the rendered pages into a PPTX."""

from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from doctor import build_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report()
    tools = report["tools"]
    if not report["capabilities"].get("html_export"):
        parser.error("Playwright/Chromium is unavailable")
    export_env = os.environ.copy()
    if tools.get("playwright_node_path"):
        export_env["NODE_PATH"] = tools["playwright_node_path"]
    pptx_env = os.environ.copy()
    if tools.get("node_path"):
        pptx_env["NODE_PATH"] = tools["node_path"]
    with tempfile.TemporaryDirectory(prefix="html-to-pptx-") as directory:
        images = Path(directory)
        command = [tools["playwright_node"], str(Path(__file__).resolve().parent / "html_export.cjs"), str(args.html.resolve()), "images", str(images)]
        result = subprocess.run(command, env=export_env, check=False)
        if result.returncode:
            return result.returncode
        from PIL import Image

        rendered = sorted(images.glob("slide-*.png"))
        first = rendered[0]
        with Image.open(first) as image:
            aspect = f"{image.width}:{image.height}"
        source_html = args.html.read_text(encoding="utf-8")
        notes = [html_module.unescape(re.sub(r"<[^>]+>", "", value)).strip() for value in re.findall(r'<aside class="notes">(.*?)</aside>', source_html, re.DOTALL)]
        manifest = images / "manifest.json"
        manifest.write_text(json.dumps({"aspect_ratio": aspect, "slides": [{"path": str(image), "alt": f"Rendered HTML slide {index + 1}", "notes": notes[index] if index < len(notes) else ""} for index, image in enumerate(rendered)]}), encoding="utf-8")
        command = [tools["node"], str(Path(__file__).resolve().parent / "images_to_pptx.cjs"), str(images), str(args.output.resolve()), "--manifest", str(manifest), "--aspect-ratio", aspect]
        return subprocess.run(command, env=pptx_env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
