#!/usr/bin/env python3
"""Profile PPTX/POTX masters, layouts, slide placeholders, fonts, and colors."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
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
REMBED = f"{{{NS['r']}}}embed"


def xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(archive.read(name))


def rels(archive: zipfile.ZipFile, source: str) -> dict[str, str]:
    directory, filename = posixpath.split(source)
    name = posixpath.join(directory, "_rels", filename + ".rels")
    if name not in archive.namelist():
        return {}
    return {item.attrib.get("Id", ""): item.attrib.get("Target", "") for item in xml(archive, name).findall("pr:Relationship", NS)}


def resolve(source: str, target: str) -> str:
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def numbered(names: list[str], pattern: str) -> list[str]:
    return sorted((name for name in names if re.fullmatch(pattern, name)), key=lambda name: int(re.search(r"(\d+)\.xml$", name).group(1)))


def ordered_slides(archive: zipfile.ZipFile) -> list[str]:
    presentation_name = "ppt/presentation.xml"
    presentation = xml(archive, presentation_name)
    related = rels(archive, presentation_name)
    ordered = []
    for slide_id in presentation.findall("p:sldIdLst/p:sldId", NS):
        target = related.get(slide_id.attrib.get(RID, ""))
        if target:
            ordered.append(resolve(presentation_name, target))
    return ordered or numbered(archive.namelist(), r"ppt/slides/slide\d+\.xml")


def shape_profile(shape: ET.Element, slide_number: int) -> dict:
    kind = shape.tag.rsplit("}", 1)[-1]
    prop_paths = {"sp": "p:nvSpPr/p:cNvPr", "pic": "p:nvPicPr/p:cNvPr", "graphicFrame": "p:nvGraphicFramePr/p:cNvPr", "cxnSp": "p:nvCxnSpPr/p:cNvPr", "grpSp": "p:nvGrpSpPr/p:cNvPr"}
    placeholder_paths = {"sp": "p:nvSpPr/p:nvPr/p:ph", "pic": "p:nvPicPr/p:nvPr/p:ph", "graphicFrame": "p:nvGraphicFramePr/p:nvPr/p:ph"}
    xfrm_paths = {"sp": "p:spPr/a:xfrm", "pic": "p:spPr/a:xfrm", "graphicFrame": "p:xfrm", "cxnSp": "p:spPr/a:xfrm", "grpSp": "p:grpSpPr/a:xfrm"}
    props = shape.find(prop_paths.get(kind, ""), NS) if kind in prop_paths else None
    placeholder = shape.find(placeholder_paths.get(kind, ""), NS) if kind in placeholder_paths else None
    shape_id = int(props.attrib.get("id", 0)) if props is not None else 0
    paragraphs = []
    for p_index, paragraph in enumerate(shape.findall(".//a:p", NS)):
        runs = []
        for r_index, run in enumerate(paragraph.findall("a:r", NS)):
            node = run.find("a:t", NS)
            if node is not None:
                properties = run.find("a:rPr", NS)
                font_size = int(properties.attrib.get("sz", 1800)) / 100 if properties is not None else 18
                runs.append({"run": r_index, "text": node.text or "", "slot_id": f"s{slide_number}_sh{shape_id}_p{p_index}r{r_index}", "font_size_pt": font_size})
        if runs:
            paragraphs.append({"paragraph": p_index, "text": "".join(item["text"] for item in runs), "runs": runs})
    xfrm = shape.find(xfrm_paths.get(kind, ""), NS) if kind in xfrm_paths else None
    bounds = None
    if xfrm is not None:
        off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
        if off is not None and ext is not None:
            bounds = {"x": int(off.attrib.get("x", 0)), "y": int(off.attrib.get("y", 0)), "cx": int(ext.attrib.get("cx", 0)), "cy": int(ext.attrib.get("cy", 0))}
    record = {
        "kind": kind,
        "shape_id": shape_id,
        "name": props.attrib.get("name", "") if props is not None else "",
        "placeholder": ({"type": placeholder.attrib.get("type", "body"), "idx": int(placeholder.attrib.get("idx", 0))} if placeholder is not None else None),
        "bounds_emu": bounds,
        "paragraphs": paragraphs,
    }
    blip = shape.find(".//a:blip", NS)
    chart = shape.find(".//{http://schemas.openxmlformats.org/drawingml/2006/chart}chart", NS)
    record["image_relationship_id"] = blip.attrib.get(REMBED) if blip is not None else None
    record["chart_relationship_id"] = chart.attrib.get(RID) if chart is not None else None
    record["is_table"] = shape.find(".//a:tbl", NS) is not None
    record["alt_text"] = props.attrib.get("descr", "") if props is not None else ""
    return record


def theme_profile(root: ET.Element) -> dict:
    major = root.find(".//a:themeElements/a:fontScheme/a:majorFont", NS)
    minor = root.find(".//a:themeElements/a:fontScheme/a:minorFont", NS)
    colors = []
    for node in root.findall(".//a:themeElements/a:clrScheme/*/*", NS):
        value = node.attrib.get("val") or node.attrib.get("lastClr")
        if value and value not in colors:
            colors.append(value)
    def fonts(node: ET.Element | None) -> dict:
        if node is None:
            return {}
        latin, east_asian = node.find("a:latin", NS), node.find("a:ea", NS)
        return {"latin": latin.attrib.get("typeface", "") if latin is not None else "", "east_asian": east_asian.attrib.get("typeface", "") if east_asian is not None else ""}
    return {"major_fonts": fonts(major), "minor_fonts": fonts(minor), "colors": colors}


def profile(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        presentation = xml(archive, "ppt/presentation.xml")
        size = presentation.find("p:sldSz", NS)
        report = {
            "schema": "ppt-template-profile/v1",
            "template": str(path),
            "slide_size_emu": {"width": int(size.attrib.get("cx", 0)), "height": int(size.attrib.get("cy", 0))} if size is not None else {},
            "themes": [], "masters": [], "layouts": [], "slides": [],
        }
        for name in numbered(names, r"ppt/theme/theme\d+\.xml"):
            report["themes"].append({"part": name, **theme_profile(xml(archive, name))})
        for name in numbered(names, r"ppt/slideMasters/slideMaster\d+\.xml"):
            root = xml(archive, name)
            report["masters"].append({"part": name, "name": root.find("p:cSld", NS).attrib.get("name", "") if root.find("p:cSld", NS) is not None else ""})
        for name in numbered(names, r"ppt/slideLayouts/slideLayout\d+\.xml"):
            root = xml(archive, name)
            c_sld = root.find("p:cSld", NS)
            report["layouts"].append({"part": name, "name": c_sld.attrib.get("name", "") if c_sld is not None else "", "type": root.attrib.get("type", ""), "matching_name": root.attrib.get("matchingName", ""), "placeholder_count": len(root.findall(".//p:ph", NS))})
        for index, name in enumerate(ordered_slides(archive), 1):
            root = xml(archive, name)
            related = rels(archive, name)
            layout = next((resolve(name, target) for rid, target in related.items() if "slideLayout" in target), None)
            accepted = {"sp", "pic", "graphicFrame", "cxnSp", "grpSp"}
            shapes = [shape_profile(shape, index) for shape in root.find("p:cSld/p:spTree", NS).iter() if shape.tag.rsplit("}", 1)[-1] in accepted] if root.find("p:cSld/p:spTree", NS) is not None else []
            report["slides"].append({"number": index, "part": name, "layout": layout, "text": " ".join(node.text or "" for node in root.findall(".//a:t", NS)).strip(), "shapes": shapes})
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = profile(args.template.resolve())
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(f"Created {output}\nSlides: {len(report['slides'])}\nLayouts: {len(report['layouts'])}\nMasters: {len(report['masters'])}")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
