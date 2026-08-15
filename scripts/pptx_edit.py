#!/usr/bin/env python3
"""Apply text, image, notes, chart, and slide-order edits to an existing PPTX."""

from __future__ import annotations

import argparse
import io
import json
import posixpath
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from template_fill import NS, RID, fill, relationship_targets, slide_parts


NS.update({"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"})
REMBED = f"{{{NS['r']}}}embed"
for prefix, uri in NS.items():
    ET.register_namespace(prefix if prefix != "pr" else "", uri)


def props_for(element: ET.Element) -> ET.Element | None:
    kind = element.tag.rsplit("}", 1)[-1]
    paths = {"sp": "p:nvSpPr/p:cNvPr", "pic": "p:nvPicPr/p:cNvPr", "graphicFrame": "p:nvGraphicFramePr/p:cNvPr", "cxnSp": "p:nvCxnSpPr/p:cNvPr", "grpSp": "p:nvGrpSpPr/p:cNvPr"}
    return element.find(paths.get(kind, ""), NS) if kind in paths else None


def element_by_id(root: ET.Element, shape_id: int) -> ET.Element | None:
    for element in root.iter():
        props = props_for(element)
        if props is not None and int(props.attrib.get("id", -1)) == shape_id:
            return element
    return None


def rels_name(slide_part: str) -> str:
    directory, filename = posixpath.split(slide_part)
    return posixpath.join(directory, "_rels", filename + ".rels")


def rel_map(root: ET.Element) -> dict[str, ET.Element]:
    return {item.attrib.get("Id", ""): item for item in root.findall("pr:Relationship", NS)}


def resolve(source: str, target: str) -> str:
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def replace_notes(parts: dict[str, bytes], slide_part: str, text: str) -> None:
    relation_part = rels_name(slide_part)
    if relation_part not in parts:
        raise ValueError(f"slide has no notes relationship: {slide_part}")
    rel_root = ET.fromstring(parts[relation_part])
    note_target = next((item.attrib.get("Target", "") for item in rel_root.findall("pr:Relationship", NS) if item.attrib.get("Type", "").endswith("/notesSlide")), None)
    if not note_target:
        raise ValueError(f"slide has no notes part: {slide_part}")
    note_part = resolve(slide_part, note_target)
    root = ET.fromstring(parts[note_part])
    body = next((shape for shape in root.findall(".//p:sp", NS) if (shape.find("p:nvSpPr/p:nvPr/p:ph", NS) is not None and shape.find("p:nvSpPr/p:nvPr/p:ph", NS).attrib.get("type", "body") == "body")), None)
    target = body or root
    nodes = target.findall(".//a:t", NS)
    if not nodes:
        raise ValueError(f"notes body has no text nodes: {note_part}")
    nodes[0].text = text
    for node in nodes[1:]:
        node.text = ""
    parts[note_part] = ET.tostring(root, encoding="utf-8", xml_declaration=True)


def replace_image(parts: dict[str, bytes], slide_part: str, edit: dict) -> None:
    slide = ET.fromstring(parts[slide_part])
    shape = element_by_id(slide, int(edit["shape_id"]))
    if shape is None or shape.tag.rsplit("}", 1)[-1] != "pic":
        raise ValueError(f"picture shape {edit['shape_id']} was not found")
    blip = shape.find(".//a:blip", NS)
    rid = blip.attrib.get(REMBED, "") if blip is not None else ""
    relation_part = rels_name(slide_part)
    rel_root = ET.fromstring(parts[relation_part])
    relationship = rel_map(rel_root).get(rid)
    if relationship is None:
        raise ValueError(f"picture relationship {rid!r} was not found")
    source = Path(edit["path"]).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"replacement image does not exist: {source}")
    slide_number = int(re.search(r"slide(\d+)\.xml", slide_part).group(1))
    extension = source.suffix.lower().lstrip(".") or "png"
    media_part = f"ppt/media/pptgen-s{slide_number}-sh{edit['shape_id']}.{extension}"
    relationship.attrib["Target"] = f"../media/{posixpath.basename(media_part)}"
    parts[relation_part] = ET.tostring(rel_root, encoding="utf-8", xml_declaration=True)
    parts[media_part] = source.read_bytes()
    if edit.get("alt"):
        props = props_for(shape)
        if props is not None:
            props.attrib["descr"] = str(edit["alt"])
            parts[slide_part] = ET.tostring(slide, encoding="utf-8", xml_declaration=True)
    content_types = ET.fromstring(parts["[Content_Types].xml"])
    content_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    existing = {item.attrib.get("Extension", "").lower() for item in content_types.findall(f"{{{content_ns}}}Default")}
    if extension not in existing:
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}.get(extension, f"image/{extension}")
        ET.SubElement(content_types, f"{{{content_ns}}}Default", {"Extension": extension, "ContentType": mime})
        parts["[Content_Types].xml"] = ET.tostring(content_types, encoding="utf-8", xml_declaration=True)


def replace_cache(cache: ET.Element | None, values: list, numeric: bool) -> None:
    if cache is None:
        return
    for child in list(cache):
        if child.tag in {f"{{{NS['c']}}}pt", f"{{{NS['c']}}}ptCount"}:
            cache.remove(child)
    count = ET.SubElement(cache, f"{{{NS['c']}}}ptCount", {"val": str(len(values))})
    for index, value in enumerate(values):
        point = ET.SubElement(cache, f"{{{NS['c']}}}pt", {"idx": str(index)})
        ET.SubElement(point, f"{{{NS['c']}}}v").text = str(float(value) if numeric else value)


def chart_rels_name(chart_part: str) -> str:
    directory, filename = posixpath.split(chart_part)
    return posixpath.join(directory, "_rels", filename + ".rels")


def parse_formula(formula: str) -> tuple[str, str, int, str, int]:
    match = re.fullmatch(r"'?([^']+)'?!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?", formula)
    if not match:
        raise ValueError(f"unsupported chart formula: {formula}")
    return match.group(1), match.group(2), int(match.group(3)), match.group(4) or match.group(2), int(match.group(5) or match.group(3))


def column_number(letters: str) -> int:
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value


def column_letters(number: int) -> str:
    value = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        value = chr(65 + remainder) + value
    return value


def set_sheet_values(root: ET.Element, start_col: str, start_row: int, values: list, numeric: bool) -> None:
    sheet_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet_data = root.find(f"{{{sheet_ns}}}sheetData")
    column = column_number(start_col)
    rows = {int(row.attrib["r"]): row for row in sheet_data.findall(f"{{{sheet_ns}}}row")}
    for offset, value in enumerate(values):
        row_number = start_row + offset
        row = rows.get(row_number)
        if row is None:
            row = ET.SubElement(sheet_data, f"{{{sheet_ns}}}row", {"r": str(row_number)})
            rows[row_number] = row
        reference = f"{column_letters(column)}{row_number}"
        cell = next((item for item in row.findall(f"{{{sheet_ns}}}c") if item.attrib.get("r") == reference), None)
        if cell is None:
            cell = ET.SubElement(row, f"{{{sheet_ns}}}c", {"r": reference})
        for child in list(cell):
            cell.remove(child)
        if numeric:
            cell.attrib["t"] = "n"
            ET.SubElement(cell, f"{{{sheet_ns}}}v").text = str(float(value))
        else:
            cell.attrib["t"] = "inlineStr"
            inline = ET.SubElement(cell, f"{{{sheet_ns}}}is")
            ET.SubElement(inline, f"{{{sheet_ns}}}t").text = str(value)


def update_embedded_workbook(parts: dict[str, bytes], chart_part: str, chart: ET.Element, edit: dict) -> bool:
    relation_part = chart_rels_name(chart_part)
    if relation_part not in parts:
        return False
    rel_root = ET.fromstring(parts[relation_part])
    package = next((item for item in rel_root.findall("pr:Relationship", NS) if item.attrib.get("Type", "").endswith("/package")), None)
    if package is None:
        return False
    workbook_part = resolve(chart_part, package.attrib["Target"])
    with zipfile.ZipFile(io.BytesIO(parts[workbook_part])) as archive:
        workbook_parts = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    sheet_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    office_r = NS["r"]
    workbook = ET.fromstring(workbook_parts["xl/workbook.xml"])
    workbook_rels = ET.fromstring(workbook_parts["xl/_rels/workbook.xml.rels"])
    relation_lookup = rel_map(workbook_rels)
    sheets = {}
    for sheet in workbook.findall(f".//{{{sheet_ns}}}sheet"):
        relation = relation_lookup.get(sheet.attrib.get(f"{{{office_r}}}id", ""))
        if relation is not None:
            sheets[sheet.attrib["name"]] = resolve("xl/workbook.xml", relation.attrib["Target"])

    updates = []
    for series_node, series in zip(chart.findall(".//c:ser", NS), edit.get("series") or []):
        name_formula = series_node.find("c:tx/c:strRef/c:f", NS)
        category_formula = series_node.find("c:cat//c:f", NS)
        category_numeric = series_node.find("c:cat/c:numRef/c:f", NS) is not None
        value_formula = series_node.find("c:val/c:numRef/c:f", NS)
        if name_formula is not None and series.get("name"):
            updates.append((name_formula.text, [series["name"]], False))
        if category_formula is not None:
            updates.append((category_formula.text, edit.get("categories") or [], category_numeric))
        if value_formula is not None:
            updates.append((value_formula.text, series.get("values") or [], True))
    for formula, values, numeric in updates:
        sheet_name, start_col, start_row, _, _ = parse_formula(formula)
        worksheet_part = sheets.get(sheet_name)
        if not worksheet_part:
            raise ValueError(f"chart worksheet {sheet_name!r} was not found")
        root = ET.fromstring(workbook_parts[worksheet_part])
        set_sheet_values(root, start_col, start_row, values, bool(numeric))
        workbook_parts[worksheet_part] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in workbook_parts.items():
            archive.writestr(name, data)
    parts[workbook_part] = buffer.getvalue()
    return True


def replace_chart(parts: dict[str, bytes], slide_part: str, edit: dict) -> None:
    slide = ET.fromstring(parts[slide_part])
    shape = element_by_id(slide, int(edit["shape_id"]))
    if shape is None:
        raise ValueError(f"chart shape {edit['shape_id']} was not found")
    chart_ref = shape.find(".//c:chart", NS)
    rid = chart_ref.attrib.get(RID, "") if chart_ref is not None else ""
    rel_root = ET.fromstring(parts[rels_name(slide_part)])
    relationship = rel_map(rel_root).get(rid)
    if relationship is None:
        raise ValueError(f"chart relationship {rid!r} was not found")
    chart_part = resolve(slide_part, relationship.attrib["Target"])
    chart = ET.fromstring(parts[chart_part])
    categories = edit.get("categories") or []
    series_data = edit.get("series") or []
    series_nodes = chart.findall(".//c:ser", NS)
    if len(series_data) != len(series_nodes):
        raise ValueError(f"chart series count mismatch: source={len(series_nodes)} edit={len(series_data)}")
    for node, values in zip(series_nodes, series_data):
        replace_cache(node.find("c:cat/c:strRef/c:strCache", NS), categories, False)
        replace_cache(node.find("c:cat/c:numRef/c:numCache", NS), categories, True)
        replace_cache(node.find("c:val/c:numRef/c:numCache", NS), values.get("values") or [], True)
        name = node.find("c:tx/c:strRef/c:strCache", NS)
        if values.get("name") and name is not None:
            replace_cache(name, [values["name"]], False)
    update_embedded_workbook(parts, chart_part, chart, edit)
    parts[chart_part] = ET.tostring(chart, encoding="utf-8", xml_declaration=True)


def duplicate_slide(parts: dict[str, bytes], source_part: str) -> str:
    presentation = ET.fromstring(parts["ppt/presentation.xml"])
    presentation_rels = ET.fromstring(parts["ppt/_rels/presentation.xml.rels"])
    relationships = rel_map(presentation_rels)
    source_rid = next((rid for rid, item in relationships.items() if resolve("ppt/presentation.xml", item.attrib.get("Target", "")) == source_part), None)
    if not source_rid:
        raise ValueError(f"presentation relationship for {source_part} was not found")
    existing_numbers = [int(match.group(1)) for name in parts for match in [re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)] if match]
    new_number = max(existing_numbers, default=0) + 1
    new_part = f"ppt/slides/slide{new_number}.xml"
    parts[new_part] = parts[source_part]
    source_rels = rels_name(source_part)
    if source_rels in parts:
        rel_root = ET.fromstring(parts[source_rels])
        for item in list(rel_root):
            if item.attrib.get("Type", "").endswith(("/notesSlide", "/comments", "/comment")):
                rel_root.remove(item)
        parts[rels_name(new_part)] = ET.tostring(rel_root, encoding="utf-8", xml_declaration=True)
    used_rids = [int(match.group(1)) for rid in relationships for match in [re.fullmatch(r"rId(\d+)", rid)] if match]
    new_rid = f"rId{max(used_rids, default=0) + 1}"
    ET.SubElement(presentation_rels, f"{{{NS['pr']}}}Relationship", {"Id": new_rid, "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", "Target": f"slides/slide{new_number}.xml"})
    slide_list = presentation.find("p:sldIdLst", NS)
    source_node = next(node for node in slide_list if node.attrib.get(RID) == source_rid)
    ids = [int(node.attrib.get("id", 255)) for node in slide_list]
    new_node = ET.Element(f"{{{NS['p']}}}sldId", {"id": str(max(ids, default=255) + 1), RID: new_rid})
    slide_list.insert(list(slide_list).index(source_node) + 1, new_node)
    content_types = ET.fromstring(parts["[Content_Types].xml"])
    content_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.SubElement(content_types, f"{{{content_ns}}}Override", {"PartName": f"/{new_part}", "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"})
    parts["ppt/presentation.xml"] = ET.tostring(presentation, encoding="utf-8", xml_declaration=True)
    parts["ppt/_rels/presentation.xml.rels"] = ET.tostring(presentation_rels, encoding="utf-8", xml_declaration=True)
    parts["[Content_Types].xml"] = ET.tostring(content_types, encoding="utf-8", xml_declaration=True)
    return new_part


def edit_pptx(source: Path, spec_path: Path, output: Path, profile: Path | None, strict: bool) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="pptx-edit-") as directory:
        text_stage = Path(directory) / "text-stage.pptx"
        fill(source, spec_path, text_stage, profile, strict)
        with zipfile.ZipFile(text_stage) as archive:
            parts = {info.filename: archive.read(info.filename) for info in archive.infolist()}
            infos = {info.filename: info for info in archive.infolist()}
            ordered = slide_parts(archive)
        for slide_number in spec.get("duplicate_slides", []):
            duplicate_slide(parts, ordered[int(slide_number) - 1])
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as handle:
            order_probe = Path(handle.name)
        try:
            with zipfile.ZipFile(order_probe, "w") as archive:
                for name, data in parts.items():
                    archive.writestr(name, data)
            with zipfile.ZipFile(order_probe) as archive:
                ordered = slide_parts(archive)
        finally:
            order_probe.unlink(missing_ok=True)
        for edit in spec.get("images", []):
            replace_image(parts, ordered[int(edit["slide"]) - 1], edit)
        for edit in spec.get("notes", []):
            replace_notes(parts, ordered[int(edit["slide"]) - 1], str(edit.get("text", "")))
        for edit in spec.get("charts", []):
            replace_chart(parts, ordered[int(edit["slide"]) - 1], edit)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in parts.items():
                archive.writestr(infos.get(name, name), data)
    return {"output": str(output), "text_edits": len(spec.get("edits", [])), "image_edits": len(spec.get("images", [])), "note_edits": len(spec.get("notes", [])), "chart_edits": len(spec.get("charts", [])), "duplicated_slides": len(spec.get("duplicate_slides", []))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = edit_pptx(args.source.resolve(), args.spec.resolve(), args.output.resolve(), args.profile.resolve() if args.profile else None, args.strict)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
