#!/usr/bin/env python3
"""Report which PPT generation and verification capabilities are available."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


TOOL_CANDIDATES = {
    "soffice": [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOfficeDev.app/Contents/MacOS/soffice",
    ],
    "pdftoppm": [],
    "pdftotext": [],
    "tesseract": [],
    "swift": [],
    "chrome": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "node": [],
}


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in TOOL_CANDIDATES.get(name, []):
        if Path(candidate).is_file():
            return candidate
    return None


def node_module(node: str | None, module: str, node_path: str | None = None) -> str | None:
    if not node:
        return None
    env = os.environ.copy()
    if node_path:
        current = env.get("NODE_PATH")
        env["NODE_PATH"] = node_path if not current else f"{node_path}{os.pathsep}{current}"
    result = subprocess.run(
        [node, "-e", f"process.stdout.write(require.resolve('{module}'))"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def find_node_with_module(module: str) -> tuple[str | None, str | None, str | None]:
    candidates: list[tuple[str, str | None]] = []
    default_node = find_tool("node")
    if default_node:
        candidates.append((default_node, None))
    runtime_root = Path.home() / ".cache" / "codex-runtimes"
    for node in sorted(runtime_root.glob("*/dependencies/node/bin/node"), reverse=True):
        candidates.append((str(node), str(node.parent.parent / "node_modules")))

    seen = set()
    for node, node_path in candidates:
        key = (node, node_path)
        if key in seen:
            continue
        seen.add(key)
        resolved = node_module(node, module, node_path)
        if resolved:
            return node, node_path, resolved
    return default_node, None, None


def build_report() -> dict:
    node, node_path, pptxgenjs = find_node_with_module("pptxgenjs")
    playwright_node, playwright_node_path, playwright = find_node_with_module("playwright")
    soffice = find_tool("soffice") or find_tool("libreoffice")
    pdftoppm = find_tool("pdftoppm")
    pdftotext = find_tool("pdftotext")
    tesseract = find_tool("tesseract")
    swift = find_tool("swift")
    chrome = find_tool("chrome") or find_tool("chromium") or find_tool("google-chrome")
    pillow = importlib.util.find_spec("PIL") is not None
    scripts = Path(__file__).resolve().parent
    macos_vision = bool(platform.system() == "Darwin" and swift and (scripts / "macos_vision_ocr.swift").is_file())
    macos_pdfkit = bool(platform.system() == "Darwin" and swift and (scripts / "macos_pdf_text.swift").is_file())

    return {
        "python": sys.executable,
        "tools": {
            "node": node,
            "node_path": node_path,
            "pptxgenjs": pptxgenjs,
            "playwright_node": playwright_node,
            "playwright_node_path": playwright_node_path,
            "playwright": playwright,
            "soffice": soffice,
            "pdftoppm": pdftoppm,
            "pdftotext": pdftotext,
            "tesseract": tesseract,
            "swift": swift,
            "chrome": chrome,
            "pillow": pillow,
        },
        "capabilities": {
            "inspect_pptx": True,
            "native_pptx_generation": bool(node and pptxgenjs and (scripts / "build_pptx.cjs").is_file()),
            "render_pptx": bool(soffice and pdftoppm),
            "html_deck": (scripts / "build_html.py").is_file(),
            "html_export": bool(playwright_node and playwright and chrome and (scripts / "html_export.cjs").is_file()),
            "image_first_pptx": bool(node and pptxgenjs and (scripts / "images_to_pptx.cjs").is_file()),
            "template_profile": (scripts / "template_profile.py").is_file(),
            "template_fill": (scripts / "template_fill.py").is_file(),
            "source_ingestion": (scripts / "ingest.py").is_file(),
            "pdf_text_extraction": bool(pdftotext or macos_pdfkit),
            "pdf_text_pdftotext": bool(pdftotext),
            "pdf_text_macos_pdfkit": macos_pdfkit,
            "ocr_reconstruction": bool(tesseract or macos_vision),
            "ocr_tesseract": bool(tesseract),
            "ocr_macos_vision": macos_vision,
            "png_contact_sheet": bool(pillow),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail unless native PPTX generation and rendering are available",
    )
    args = parser.parse_args()
    report = build_report()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(f"Python: {report['python']}")
        for name, value in report["tools"].items():
            shown = value if value not in (None, False) else "missing"
            if value is True:
                shown = "available"
            print(f"{name}: {shown}")
        print("Capabilities:")
        for name, available in report["capabilities"].items():
            print(f"  {'yes' if available else 'no ':3} {name}")

    required = (
        report["capabilities"]["native_pptx_generation"],
        report["capabilities"]["render_pptx"],
    )
    return 1 if args.strict and not all(required) else 0


if __name__ == "__main__":
    raise SystemExit(main())
