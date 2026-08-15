#!/usr/bin/env python3
"""Render PPT/PPTX or PDF pages to PNG and create a contact sheet."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


SOFFICE_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/Applications/LibreOfficeDev.app/Contents/MacOS/soffice",
]


def find_tool(name: str, candidates: list[str] | None = None) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in candidates or []:
        if Path(candidate).is_file():
            return candidate
    return None


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{detail}")


def clean_generated(output_dir: Path, pdf_name: str | None) -> None:
    for pattern in ("slide-*.png", "contact-sheet.html", "contact-sheet.png"):
        for path in output_dir.glob(pattern):
            path.unlink()
    if pdf_name:
        pdf = output_dir / pdf_name
        if pdf.exists():
            pdf.unlink()


def make_html(images: list[Path], output_dir: Path) -> Path:
    cards = []
    for index, image in enumerate(images, start=1):
        cards.append(
            "<figure><img src=\"{}\" alt=\"Slide {}\"><figcaption>Slide {}</figcaption></figure>".format(
                html.escape(image.name), index, index
            )
        )
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Slide contact sheet</title><style>
body{margin:24px;background:#e8eaed;color:#202124;font:14px system-ui,sans-serif}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}
figure{margin:0;background:white;padding:10px;border:1px solid #c8ccd0;box-shadow:0 2px 8px #0002}
img{display:block;width:100%;height:auto;background:white}figcaption{padding:8px 2px 0;font-weight:600}
</style></head><body><main>""" + "".join(cards) + "</main></body></html>\n"
    path = output_dir / "contact-sheet.html"
    path.write_text(document, encoding="utf-8")
    return path


def make_png(images: list[Path], output_dir: Path, columns: int = 4) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        return None
    opened = [Image.open(path).convert("RGB") for path in images]
    if not opened:
        return None
    thumb_width = 480
    gap = 24
    label_height = 28
    thumbs = []
    for image in opened:
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, max(1, int(image.height * ratio))))
        thumbs.append(ImageOps.expand(thumb, border=1, fill="#aeb4ba"))
    cell_height = max(image.height for image in thumbs) + label_height
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gap, rows * cell_height + (rows + 1) * gap),
        "#e8eaed",
    )
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(thumbs):
        row, column = divmod(index, columns)
        x = gap + column * (thumb_width + gap)
        y = gap + row * (cell_height + gap)
        sheet.paste(image, (x, y))
        draw.text((x, y + image.height + 6), f"Slide {index + 1}", fill="#202124")
    path = output_dir / "contact-sheet.png"
    sheet.save(path)
    return path


def page_number(path: Path) -> int:
    match = re.search(r"-(\d+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        parser.error(f"Input does not exist: {source}")
    output_dir = (args.output_dir or source.parent / f"{source.stem}-rendered").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_pdf_name = f"{source.stem}.pdf" if source.suffix.lower() != ".pdf" else None
    if args.clean:
        clean_generated(output_dir, generated_pdf_name)

    if source.suffix.lower() == ".pdf":
        pdf = source
    else:
        soffice = find_tool("soffice", SOFFICE_CANDIDATES) or find_tool("libreoffice")
        if not soffice:
            raise SystemExit("LibreOffice/soffice is required to render PPT/PPTX files")
        profile = Path(tempfile.mkdtemp(prefix="ppt-gen-lo-"))
        try:
            run(
                [
                    soffice,
                    f"-env:UserInstallation={profile.as_uri()}",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(source),
                ]
            )
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        pdf = output_dir / f"{source.stem}.pdf"
        if not pdf.is_file():
            raise SystemExit(f"Renderer did not create {pdf}")

    pdftoppm = find_tool("pdftoppm")
    if not pdftoppm:
        raise SystemExit("pdftoppm is required to render PDF pages")
    run([pdftoppm, "-png", "-r", str(args.dpi), str(pdf), str(output_dir / "slide")])
    images = sorted(output_dir.glob("slide-*.png"), key=page_number)
    if not images:
        raise SystemExit("No slide images were rendered")
    html_path = make_html(images, output_dir)
    png_path = make_png(images, output_dir, max(1, args.columns))

    print(f"PDF: {pdf}")
    print(f"Slides: {len(images)}")
    print(f"HTML contact sheet: {html_path}")
    if png_path:
        print(f"PNG contact sheet: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
