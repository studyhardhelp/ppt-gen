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
    r"\b(?:TODO|TBD|LOREM(?: IPSUM)?|PLACEHOLDER|SAMPLE (?:TEXT|TITLE|DATA)|"
    r"INSERT (?:TEXT|IMAGE|CHART)|CLICK TO (?:ADD|EDIT)|TYPE HERE|YOUR (?:TEXT|TITLE|"
    r"SUBTITLE|COMPANY|LOGO)|QUESTION\s*\d+|KEY\s*WORDS?\s*(?:HERE)?|RICE HUSK)\b|"
    r"待补充|待填写|占位|请输入|单击此处|在此输入|示例(?:文字|标题|数据)",
    re.IGNORECASE,
)
EMU_PER_POINT = 12700


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


def shape_records(slide: ET.Element) -> list[dict]:
    sp_tree = slide.find("p:cSld/p:spTree", NS)
    if sp_tree is None:
        return []
    records = []
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
        props = child.find("p:nvSpPr/p:cNvPr", NS) if kind == "sp" else None
        text = text_for(child)
        sizes = []
        for node in child.findall(".//*[@sz]"):
            try:
                sizes.append(int(node.attrib["sz"]) / 100)
            except (KeyError, ValueError):
                pass
        records.append(
            {
                "kind": kind,
                "id": int(props.attrib.get("id", 0)) if props is not None else 0,
                "name": props.attrib.get("name", "") if props is not None else "",
                "x": int(off.attrib.get("x", 0)),
                "y": int(off.attrib.get("y", 0)),
                "cx": int(ext.attrib.get("cx", 0)),
                "cy": int(ext.attrib.get("cy", 0)),
                "text": text,
                "font_size": max(sizes, default=18),
            }
        )
    return records


def visual_width(text: str) -> float:
    width = 0.0
    for character in text:
        if "\u4e00" <= character <= "\u9fff" or "\u3000" <= character <= "\u303f" or "\uff00" <= character <= "\uffef":
            width += 1.0
        elif character.isspace():
            width += 0.35
        elif character.isascii():
            width += 0.52
        else:
            width += 0.8
    return width


def likely_overflow(record: dict) -> bool:
    text = record["text"]
    if not text or record["cx"] <= 0 or record["cy"] <= 0:
        return False
    font = max(8.0, float(record["font_size"]))
    width_points = record["cx"] / EMU_PER_POINT
    height_points = record["cy"] / EMU_PER_POINT
    chars_per_line = max(1.0, width_points / (font * 0.62))
    lines = max(1, int(height_points / (font * 1.15)))
    needed = sum(max(1.0, visual_width(segment) / chars_per_line) for segment in text.splitlines() or [text])
    return needed > lines * 1.25


def overlap_ratio(left: dict, right: dict) -> float:
    x1, y1 = max(left["x"], right["x"]), max(left["y"], right["y"])
    x2 = min(left["x"] + left["cx"], right["x"] + right["cx"])
    y2 = min(left["y"] + left["cy"], right["y"] + right["cy"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    intersection = (x2 - x1) * (y2 - y1)
    smaller = min(left["cx"] * left["cy"], right["cx"] * right["cy"])
    return intersection / smaller if smaller else 0.0


def text_collisions(records: list[dict]) -> list[tuple[dict, dict]]:
    text_boxes = [record for record in records if record["kind"] == "sp" and len(record["text"].strip()) >= 4]
    collisions = []
    for index, left in enumerate(text_boxes):
        for right in text_boxes[index + 1 :]:
            ratio = overlap_ratio(left, right)
            contains = (
                left["x"] <= right["x"] and left["y"] <= right["y"]
                and left["x"] + left["cx"] >= right["x"] + right["cx"]
                and left["y"] + left["cy"] >= right["y"] + right["cy"]
            ) or (
                right["x"] <= left["x"] and right["y"] <= left["y"]
                and right["x"] + right["cx"] >= left["x"] + left["cx"]
                and right["y"] + right["cy"] >= left["y"] + left["cy"]
            )
            if ratio >= 0.22 and not contains:
                collisions.append((left, right))
    return collisions


def referenced_fonts(slide: ET.Element) -> list[str]:
    fonts = set()
    for node in slide.findall(".//*[@typeface]"):
        value = node.attrib.get("typeface", "").strip()
        if value and not value.startswith("+"):
            fonts.add(value)
    return sorted(fonts)


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
        fingerprints: dict[str, int] = {}
        all_fonts: set[str] = set()
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
                samples = ", ".join(match if isinstance(match, str) else "".join(match) for match in placeholders[:3])
                report["issues"].append(
                    {
                        "level": "warning",
                        "slide": index,
                        "message": f"Possible placeholder text remains: {samples}",
                    }
                )
            records = shape_records(slide)
            for record in records:
                kind, x, y, cx, cy = (record[key] for key in ("kind", "x", "y", "cx", "cy"))
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
                if likely_overflow(record):
                    label = record["name"] or f"shape {record['id']}"
                    report["issues"].append(
                        {
                            "level": "warning",
                            "slide": index,
                            "message": f"Possible text overflow in {label}",
                        }
                    )
            for left, right in text_collisions(records):
                left_label = left["name"] or f"shape {left['id']}"
                right_label = right["name"] or f"shape {right['id']}"
                report["issues"].append(
                    {
                        "level": "warning",
                        "slide": index,
                        "message": f"Possible text collision: {left_label} and {right_label}",
                    }
                )

            normalized = re.sub(r"\s+", " ", text).strip().lower()
            if normalized and normalized in fingerprints:
                report["issues"].append(
                    {
                        "level": "warning",
                        "slide": index,
                        "message": f"Text duplicates slide {fingerprints[normalized]}",
                    }
                )
            elif normalized:
                fingerprints[normalized] = index
            fonts = referenced_fonts(slide)
            all_fonts.update(fonts)

            report["slides"].append(
                {
                    "number": index,
                    "part": slide_name,
                    "title": title_for(slide),
                    "text_characters": len(text),
                    "media_relationships": media,
                    "external_links": external_links,
                    "has_notes": notes,
                    "fonts": fonts,
                }
            )
        report["fonts"] = sorted(all_fonts)
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
