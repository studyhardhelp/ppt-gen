#!/usr/bin/env python3
"""Inspect a PPTX package for structural and slide-level quality risks."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
RID = f"{{{NS['r']}}}id"
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|LOREM IPSUM|PLACEHOLDER|INSERT (?:TEXT|IMAGE|CHART))\b|待补充|占位",
    re.IGNORECASE,
)


def parse_xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(archive.read(name))


def relationship_map(archive: zipfile.ZipFile, rels_name: str) -> dict[str, dict]:
    if rels_name not in archive.namelist():
        return {}
    root = parse_xml(archive, rels_name)
    return {
        rel.attrib.get("Id", ""): {
            "target": rel.attrib.get("Target", ""),
            "type": rel.attrib.get("Type", ""),
            "external": rel.attrib.get("TargetMode") == "External",
        }
        for rel in root.findall("pr:Relationship", NS)
    }


def resolve_target(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def slide_order(archive: zipfile.ZipFile) -> list[str]:
    presentation = parse_xml(archive, "ppt/presentation.xml")
    rels = relationship_map(archive, "ppt/_rels/presentation.xml.rels")
    ordered = []
    for slide_id in presentation.findall("p:sldIdLst/p:sldId", NS):
        rel = rels.get(slide_id.attrib.get(RID, ""))
        if rel:
            ordered.append(resolve_target("ppt/presentation.xml", rel["target"]))
    if ordered:
        return ordered

    def number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ),
        key=number,
    )


def slide_size(archive: zipfile.ZipFile) -> tuple[int, int]:
    root = parse_xml(archive, "ppt/presentation.xml")
    size = root.find("p:sldSz", NS)
    if size is None:
        return 0, 0
    return int(size.attrib.get("cx", 0)), int(size.attrib.get("cy", 0))


def text_for(element: ET.Element) -> str:
    return " ".join(
        node.text.strip()
        for node in element.findall(".//a:t", NS)
        if node.text and node.text.strip()
    )


def title_for(slide: ET.Element) -> str:
    candidates = []
    for shape in slide.findall(".//p:sp", NS):
        text = text_for(shape)
        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if placeholder is not None and placeholder.attrib.get("type") in {
            "title",
            "ctrTitle",
        }:
            return text
        sizes = []
        for node in shape.findall(".//*[@sz]"):
            try:
                sizes.append(int(node.attrib["sz"]))
            except ValueError:
                pass
        if text:
            candidates.append((max(sizes, default=0), len(text), text))
    return max(candidates, default=(0, 0, ""))[2]


def shape_bounds(slide: ET.Element) -> list[tuple[str, int, int, int, int]]:
    sp_tree = slide.find("p:cSld/p:spTree", NS)
    if sp_tree is None:
        return []
    bounds = []
    for child in list(sp_tree):
        kind = child.tag.rsplit("}", 1)[-1]
        paths = {
            "sp": "p:spPr/a:xfrm",
            "pic": "p:spPr/a:xfrm",
            "cxnSp": "p:spPr/a:xfrm",
            "graphicFrame": "p:xfrm",
            "grpSp": "p:grpSpPr/a:xfrm",
        }
        path = paths.get(kind)
        if not path:
            continue
        xfrm = child.find(path, NS)
        if xfrm is None:
            continue
        off = xfrm.find("a:off", NS)
        ext = xfrm.find("a:ext", NS)
        if off is None or ext is None:
            continue
        bounds.append(
            (
                kind,
                int(off.attrib.get("x", 0)),
                int(off.attrib.get("y", 0)),
                int(ext.attrib.get("cx", 0)),
                int(ext.attrib.get("cy", 0)),
            )
        )
    return bounds


def slide_rels_name(slide_name: str) -> str:
    directory, filename = posixpath.split(slide_name)
    return posixpath.join(directory, "_rels", filename + ".rels")


def inspect(path: Path, max_text: int) -> dict:
    report = {
        "file": str(path),
        "slide_count": 0,
        "size_emu": {"width": 0, "height": 0},
        "slides": [],
        "issues": [],
    }
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        report["issues"].append({"level": "error", "message": str(exc)})
        return report

    with archive:
        corrupt = archive.testzip()
        if corrupt:
            report["issues"].append(
                {"level": "error", "message": f"Corrupt ZIP member: {corrupt}"}
            )
        required = {"[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"}
        missing = sorted(required.difference(archive.namelist()))
        for item in missing:
            report["issues"].append(
                {"level": "error", "message": f"Missing required part: {item}"}
            )
        if missing:
            return report

        width, height = slide_size(archive)
        report["size_emu"] = {"width": width, "height": height}
        slides = slide_order(archive)
        report["slide_count"] = len(slides)
        if not slides:
            report["issues"].append({"level": "error", "message": "No slides found"})

        names = set(archive.namelist())
        for index, slide_name in enumerate(slides, start=1):
            if slide_name not in names:
                report["issues"].append(
                    {
                        "level": "error",
                        "slide": index,
                        "message": f"Missing slide part: {slide_name}",
                    }
                )
                continue
            slide = parse_xml(archive, slide_name)
            text = text_for(slide)
            rels = relationship_map(archive, slide_rels_name(slide_name))
            notes = False
            external_links = 0
            media = 0
            for rel in rels.values():
                if rel["external"]:
                    external_links += 1
                    continue
                target = resolve_target(slide_name, rel["target"])
                if target not in names:
                    report["issues"].append(
                        {
                            "level": "error",
                            "slide": index,
                            "message": f"Broken relationship target: {target}",
                        }
                    )
                rel_type = rel["type"]
                notes = notes or rel_type.endswith("/notesSlide")
                media += int(
                    rel_type.endswith("/image")
                    or rel_type.endswith("/audio")
                    or rel_type.endswith("/video")
                )

            if not text and media == 0:
                report["issues"].append(
                    {"level": "warning", "slide": index, "message": "Slide is empty"}
                )
            if len(text) > max_text:
                report["issues"].append(
                    {
                        "level": "warning",
                        "slide": index,
                        "message": f"High text density: {len(text)} characters",
                    }
                )
            placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
            if placeholders:
                report["issues"].append(
                    {
                        "level": "warning",
                        "slide": index,
                        "message": "Possible placeholder text remains",
                    }
                )
            for kind, x, y, cx, cy in shape_bounds(slide):
                if x < 0 or y < 0 or cx < 0 or cy < 0:
                    report["issues"].append(
                        {
                            "level": "warning",
                            "slide": index,
                            "message": f"Negative {kind} bounds: {(x, y, cx, cy)}",
                        }
                    )
                if width and height and (x + cx > width or y + cy > height):
                    report["issues"].append(
                        {
                            "level": "warning",
                            "slide": index,
                            "message": f"{kind} extends outside the slide canvas",
                        }
                    )

            report["slides"].append(
                {
                    "number": index,
                    "part": slide_name,
                    "title": title_for(slide),
                    "text_characters": len(text),
                    "media_relationships": media,
                    "external_links": external_links,
                    "has_notes": notes,
                }
            )
    return report


def print_text(report: dict) -> None:
    size = report["size_emu"]
    print(f"File: {report['file']}")
    print(f"Slides: {report['slide_count']}")
    print(f"Canvas: {size['width']} x {size['height']} EMU")
    for slide in report["slides"]:
        title = slide["title"] or "(no title)"
        print(
            f"{slide['number']:>3}: {title[:72]} | "
            f"text={slide['text_characters']} media={slide['media_relationships']} "
            f"notes={'yes' if slide['has_notes'] else 'no'}"
        )
    if report["issues"]:
        print("Issues:")
        for issue in report["issues"]:
            prefix = f"slide {issue['slide']}: " if issue.get("slide") else ""
            print(f"  {issue['level'].upper()}: {prefix}{issue['message']}")
    else:
        print("Issues: none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    parser.add_argument("--max-text", type=int, default=900)
    args = parser.parse_args()
    report = inspect(args.pptx.resolve(), args.max_text)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text(report)
    levels = {issue["level"] for issue in report["issues"]}
    if "error" in levels:
        return 1
    if args.strict and "warning" in levels:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
