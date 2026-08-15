#!/usr/bin/env python3
"""Extract normalized text and tabular data from presentation source material."""

from __future__ import annotations

import argparse
import csv
import html.parser
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


TEXT_SUFFIXES = {".txt", ".md", ".rst", ".log"}
TABLE_SUFFIXES = {".csv", ".tsv"}
OFFICE_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


class TextHTMLParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        elif tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.findall(".//w:p", OFFICE_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", OFFICE_NS)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_pptx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = sorted((name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=lambda name: int(re.search(r"\d+", name.rsplit("/", 1)[-1]).group()))
        slides = []
        for index, name in enumerate(names, 1):
            root = ET.fromstring(archive.read(name))
            text = " ".join(node.text or "" for node in root.findall(".//a:t", OFFICE_NS)).strip()
            slides.append(f"[Slide {index}]\n{text}")
    return "\n\n".join(slides)


def extract_xlsx(path: Path) -> tuple[str, list[list[list[str]]]]:
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//s:t", namespace)) for item in root.findall("s:si", namespace)]
        sheet_names = sorted((name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)), key=lambda name: int(re.search(r"sheet(\d+)\.xml", name).group(1)))
        tables = []
        for sheet_name in sheet_names:
            root = ET.fromstring(archive.read(sheet_name))
            rows = []
            for row in root.findall(".//s:sheetData/s:row", namespace):
                values = []
                for cell in row.findall("s:c", namespace):
                    value = cell.find("s:v", namespace)
                    inline = cell.find("s:is", namespace)
                    raw = value.text if value is not None and value.text is not None else "".join(node.text or "" for node in inline.findall(".//s:t", namespace)) if inline is not None else ""
                    if cell.attrib.get("t") == "s" and raw:
                        raw = shared[int(raw)]
                    values.append(raw)
                rows.append(values)
            tables.append(rows)
    text = "\n\n".join(f"[Sheet {index}]\n" + "\n".join(" | ".join(row) for row in rows) for index, rows in enumerate(tables, 1))
    return text, tables


def extract_pdf(path: Path) -> str:
    tool = shutil.which("pdftotext")
    if not tool:
        raise RuntimeError("pdftotext is required for PDF ingestion")
    result = subprocess.run([tool, "-layout", str(path), "-"], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def extract_table(path: Path) -> tuple[str, list[list[str]]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=delimiter))
    return "\n".join(" | ".join(row) for row in rows), rows


def extract_html(raw: str) -> str:
    parser = TextHTMLParser()
    parser.feed(raw)
    return parser.text()


def fetch_url(url: str) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ppt-gen/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read(10 * 1024 * 1024)
    text = payload.decode(charset, errors="replace")
    return extract_html(text) if content_type == "text/html" else text, content_type


def extract(source: str) -> dict:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"}:
        text, kind = fetch_url(source)
        return {"source": source, "kind": kind, "text": text, "tables": []}
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    tables: list[list[list[str]]] = []
    if suffix in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
    elif suffix in TABLE_SUFFIXES:
        text, table = extract_table(path)
        tables.append(table)
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False, indent=2)
    elif suffix in {".html", ".htm"}:
        text = extract_html(path.read_text(encoding="utf-8", errors="replace"))
    elif suffix == ".docx":
        text = extract_docx(path)
    elif suffix in {".pptx", ".potx"}:
        text = extract_pptx(path)
    elif suffix == ".xlsx":
        text, tables = extract_xlsx(path)
    elif suffix == ".pdf":
        text = extract_pdf(path)
    else:
        raise ValueError(f"Unsupported input type: {suffix or '(none)'}")
    return {"source": str(path), "kind": suffix.lstrip("."), "text": text.strip(), "tables": tables}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        documents = [extract(source) for source in args.inputs]
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    result = {"schema": "ppt-gen-ingestion/v1", "documents": documents}
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {output}\nDocuments: {len(documents)}\nCharacters: {sum(len(item['text']) for item in documents)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
