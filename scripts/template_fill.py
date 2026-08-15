#!/usr/bin/env python3
"""Fill addressed text in a PPTX/POTX while preserving the package structure."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
RID = f"{{{NS['r']}}}id"


def relationship_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    name = "ppt/_rels/presentation.xml.rels"
    if name not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read(name))
    return {item.attrib.get("Id", ""): item.attrib.get("Target", "") for item in root.findall("pr:Relationship", NS)}


def slide_parts(archive: zipfile.ZipFile) -> list[str]:
    presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
    related = relationship_targets(archive)
    ordered = []
    for slide_id in presentation.findall("p:sldIdLst/p:sldId", NS):
        target = related.get(slide_id.attrib.get(RID, ""))
        if target:
            ordered.append("ppt/" + target.lstrip("/") if not target.startswith("ppt/") else target)
    return ordered or sorted((name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)))


def shape_by_id(root: ET.Element, shape_id: int) -> ET.Element | None:
    for shape in root.findall(".//p:sp", NS):
        props = shape.find("p:nvSpPr/p:cNvPr", NS)
        if props is not None and int(props.attrib.get("id", -1)) == shape_id:
            return shape
    return None


def apply_address(root: ET.Element, edit: dict, strict: bool) -> str:
    address = edit.get("address") or {}
    shape_id = int(address.get("shape_id", -1))
    shape = shape_by_id(root, shape_id)
    if shape is None:
        raise ValueError(f"shape {shape_id} was not found")
    paragraphs = shape.findall(".//a:p", NS)
    p_index = int(address.get("paragraph", 0))
    if p_index >= len(paragraphs):
        raise ValueError(f"shape {shape_id} paragraph {p_index} was not found")
    texts = paragraphs[p_index].findall(".//a:t", NS)
    if not texts:
        raise ValueError(f"shape {shape_id} paragraph {p_index} has no text runs")
    run = address.get("run")
    targets = texts if run is None else [texts[int(run)]] if int(run) < len(texts) else []
    if not targets:
        raise ValueError(f"shape {shape_id} paragraph {p_index} run {run} was not found")
    current = "".join(node.text or "" for node in targets)
    expected = edit.get("expected_text")
    if strict and expected is not None and current != expected:
        raise ValueError(f"expected {expected!r}, found {current!r} at shape {shape_id}")
    targets[0].text = str(edit.get("new_text", ""))
    for node in targets[1:]:
        node.text = ""
    return current


def resolve_slots(spec: dict, profile: dict | None) -> None:
    if not profile:
        return
    slots = {}
    for slide in profile.get("slides", []):
        for shape in slide.get("shapes", []):
            for paragraph in shape.get("paragraphs", []):
                for run in paragraph.get("runs", []):
                    slots[run["slot_id"]] = {"shape_id": shape["shape_id"], "paragraph": paragraph["paragraph"], "run": run["run"], "slide": slide["number"], "expected_text": run["text"]}
    for edit in spec.get("edits", []):
        if edit.get("slot_id"):
            slot = slots.get(edit["slot_id"])
            if not slot:
                raise ValueError(f"unknown slot_id {edit['slot_id']!r}")
            edit.setdefault("slide", slot["slide"])
            edit["address"] = {key: slot[key] for key in ("shape_id", "paragraph", "run")}
            edit.setdefault("expected_text", slot["expected_text"])


def prune_presentation(data: bytes, selected: list[int]) -> bytes:
    root = ET.fromstring(data)
    slide_list = root.find("p:sldIdLst", NS)
    if slide_list is None:
        return data
    original = list(slide_list)
    if any(number < 1 or number > len(original) for number in selected):
        raise ValueError("selected_slides contains an out-of-range slide number")
    for child in original:
        slide_list.remove(child)
    seen = set()
    for number in selected:
        if number in seen:
            raise ValueError("selected_slides cannot duplicate slides")
        seen.add(number)
        slide_list.append(original[number - 1])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def convert_potx_content_type(data: bytes) -> bytes:
    return data.replace(
        b"application/vnd.openxmlformats-officedocument.presentationml.template.main+xml",
        b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    )


def fill(template: Path, spec_path: Path, output: Path, profile_path: Path | None, strict: bool) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path else None
    resolve_slots(spec, profile)
    with zipfile.ZipFile(template) as source:
        parts = slide_parts(source)
        replacements = 0
        failures = []
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".pptx", delete=False) as handle:
            temp = Path(handle.name)
        try:
            with zipfile.ZipFile(temp, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "[Content_Types].xml" and output.suffix.lower() == ".pptx":
                        data = convert_potx_content_type(data)
                    if info.filename == "ppt/presentation.xml" and spec.get("selected_slides"):
                        data = prune_presentation(data, [int(value) for value in spec["selected_slides"]])
                    if info.filename in parts:
                        slide_number = parts.index(info.filename) + 1
                        root = ET.fromstring(data)
                        for old, new in (spec.get("global") or {}).items():
                            for node in root.findall(".//a:t", NS):
                                if node.text and old in node.text:
                                    node.text = node.text.replace(old, str(new)); replacements += 1
                        mappings = (spec.get("slides") or {}).get(str(slide_number), {})
                        for node in root.findall(".//a:t", NS):
                            if node.text in mappings:
                                node.text = str(mappings[node.text]); replacements += 1
                        for edit in spec.get("edits", []):
                            if int(edit.get("slide", 0)) == slide_number:
                                try:
                                    apply_address(root, edit, strict); replacements += 1
                                except (IndexError, ValueError) as exc:
                                    failures.append(f"slide {slide_number}: {exc}")
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    target.writestr(info, data)
            if failures and strict:
                raise ValueError("; ".join(failures))
            temp.replace(output)
        finally:
            if temp.exists():
                temp.unlink()
    return {"output": str(output), "replacements": replacements, "failures": failures, "selected_slides": spec.get("selected_slides")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", type=Path, help="Profile JSON for slot_id resolution")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = fill(args.template.resolve(), args.spec.resolve(), args.output.resolve(), args.profile.resolve() if args.profile else None, args.strict)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
