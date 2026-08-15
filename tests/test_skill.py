from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_html
import compare_renders
import ingest
import pptx_check
import template_fill
import template_profile
import templates


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>"""
ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""
PRESENTATION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>"""
PRESENTATION_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>"""


def slide_xml(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="800000" y="600000"/><a:ext cx="8000000" cy="900000"/></a:xfrm></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="2800"/><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:sld>"""


def make_pptx(path: Path, text: str = "Question 1") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/_rels/presentation.xml.rels", PRESENTATION_RELS)
        archive.writestr("ppt/slides/slide1.xml", slide_xml(text))


class SkillTests(unittest.TestCase):
    def test_placeholder_detection_includes_sample_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.pptx"
            make_pptx(path)
            report = pptx_check.inspect(path, 900)
            self.assertTrue(any("placeholder" in issue["message"].lower() for issue in report["issues"]))

    def test_template_profile_and_addressed_fill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.pptx", root / "output.pptx"
            make_pptx(source)
            profile = template_profile.profile(source)
            self.assertEqual(profile["slides"][0]["shapes"][0]["shape_id"], 2)
            spec = root / "edits.json"
            spec.write_text(json.dumps({"edits": [{"slide": 1, "address": {"shape_id": 2, "paragraph": 0, "run": 0}, "expected_text": "Question 1", "new_text": "Validated title"}]}), encoding="utf-8")
            result = template_fill.fill(source, spec, output, None, True)
            self.assertEqual(result["replacements"], 1)
            with zipfile.ZipFile(output) as archive:
                text = " ".join(node.text or "" for node in ET.fromstring(archive.read("ppt/slides/slide1.xml")).iter() if node.tag.endswith("}t"))
            self.assertEqual(text, "Validated title")

    def test_html_builder_has_themes_and_presenter_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "work").mkdir()
            (project / "work" / "brief.json").write_text(json.dumps({"title": "Demo", "theme": "technical"}), encoding="utf-8")
            (project / "work" / "storyboard.json").write_text(json.dumps({"deck": {"title": "Demo"}, "slides": [{"role": "cover", "action_title": "Demo", "speaker_note": "Talk track"}]}), encoding="utf-8")
            output = project / "deck.html"
            build_html.build(project, output, None)
            rendered = output.read_text(encoding="utf-8")
            self.assertEqual(rendered.count('<option value="'), 36)
            self.assertIn("presenter", rendered)
            self.assertIn("e.key.toLowerCase()==='s'", rendered)

    def test_ingest_markdown_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            markdown, table = root / "notes.md", root / "data.csv"
            markdown.write_text("# Finding\nEvidence", encoding="utf-8")
            table.write_text("Metric,Value\nARR,42", encoding="utf-8")
            self.assertIn("Evidence", ingest.extract(str(markdown))["text"])
            self.assertEqual(ingest.extract(str(table))["tables"][0][1], ["ARR", "42"])

    def test_ingest_xlsx_without_external_library(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "data.xlsx"
            with zipfile.ZipFile(workbook, "w") as archive:
                archive.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Metric</t></si><si><t>ARR</t></si></sst>')
                archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c t="s"><v>0</v></c><c><v>42</v></c></row><row><c t="s"><v>1</v></c><c><v>84</v></c></row></sheetData></worksheet>')
            result = ingest.extract(str(workbook))
            self.assertEqual(result["tables"][0][1], ["ARR", "84"])

    def test_render_comparison_and_local_discovery(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline", root / "candidate"
            baseline.mkdir(); candidate.mkdir()
            Image.new("RGB", (32, 18), "white").save(baseline / "slide-1.png")
            Image.new("RGB", (32, 18), "white").save(candidate / "slide-1.png")
            self.assertTrue(compare_renders.compare(baseline, candidate)["identical"])
            local = root / "local" / "demo"
            local.mkdir(parents=True)
            make_pptx(local / "template.pptx", "Demo")
            self.assertEqual(len(templates.discover_local(root / "local")), 1)


if __name__ == "__main__":
    unittest.main()
