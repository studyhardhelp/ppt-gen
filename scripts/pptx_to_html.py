#!/usr/bin/env python3
"""Convert a PPTX into a self-contained, fidelity-first HTML presentation."""

from __future__ import annotations

import argparse
import base64
import html
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pptx_check import NS, relationship_map, resolve_target, slide_order, slide_rels_name


def notes_for(archive: zipfile.ZipFile, slide_name: str) -> str:
    rels = relationship_map(archive, slide_rels_name(slide_name))
    note_part = next((resolve_target(slide_name, rel["target"]) for rel in rels.values() if rel["type"].endswith("/notesSlide") and not rel["external"]), None)
    if not note_part or note_part not in archive.namelist():
        return ""
    root = ET.fromstring(archive.read(note_part))
    values = [node.text.strip() for node in root.findall(".//a:t", NS) if node.text and node.text.strip()]
    return "\n".join(value for value in values if not re.fullmatch(r"\d+", value))


def extract_notes(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return [notes_for(archive, slide) for slide in slide_order(archive)]


def build_html(pptx: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="pptx-to-html-") as directory:
        rendered = Path(directory)
        script = Path(__file__).resolve().parent / "render_deck.py"
        result = subprocess.run([sys.executable, str(script), str(pptx), "--output-dir", str(rendered), "--clean"], capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        images = sorted(rendered.glob("slide-*.png"), key=lambda path: int(re.search(r"(\d+)$", path.stem).group(1)))
        notes = extract_notes(pptx)
        slides = []
        for index, image in enumerate(images):
            payload = base64.b64encode(image.read_bytes()).decode("ascii")
            note = html.escape(notes[index] if index < len(notes) else "")
            slides.append(f'<article class="slide" data-index="{index}"><img src="data:image/png;base64,{payload}" alt="Slide {index + 1}"><aside class="notes">{note}</aside></article>')
    title = html.escape(pptx.stem)
    document = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#080b0d;font-family:system-ui,sans-serif}}#deck{{position:absolute;left:50%;top:50%;width:1280px;height:720px;transform:translate(-50%,-50%) scale(var(--scale,1));transform-origin:center}}.slide{{display:none;position:absolute;inset:0}}.slide.active{{display:block;animation:fade .22s ease-out}}.slide img{{width:100%;height:100%;object-fit:contain;background:#fff}}.notes{{display:none}}#progress{{position:fixed;bottom:0;left:0;height:4px;background:#21b6a8}}@keyframes fade{{from{{opacity:.3}}to{{opacity:1}}}}@media print{{body{{overflow:visible;background:white}}#deck{{position:static;transform:none;width:1280px;height:auto}}.slide{{display:block;position:relative;width:1280px;height:720px;page-break-after:always}}.slide:last-child{{page-break-after:auto}}#progress{{display:none}}}}
</style></head><body><main id="deck">{"".join(slides)}</main><div id="progress"></div><script>
let current=0,presenter=null,start=Date.now();const slides=[...document.querySelectorAll('.slide')],progress=document.querySelector('#progress');function notes(){{return slides[current].querySelector('.notes')?.textContent||''}}function sync(){{if(!presenter||presenter.closed)return;presenter.document.querySelector('#count').textContent=(current+1)+' / '+slides.length;presenter.document.querySelector('#notes').textContent=notes();presenter.document.querySelector('#next').textContent=slides[current+1]?'Slide '+(current+2):'End'}}function show(n){{current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>s.classList.toggle('active',i===current));progress.style.width=((current+1)/slides.length*100)+'%';sync()}}function fit(){{document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720))}}function openPresenter(){{presenter=window.open('','pptPresenter','width=900,height=650');if(!presenter)return;presenter.document.write('<!doctype html><title>Presenter</title><style>body{{background:#111;color:#eee;font:20px system-ui;padding:28px}}#timer{{font:700 46px monospace;color:#21b6a8}}#notes{{white-space:pre-wrap;line-height:1.5}}</style><div id="timer">00:00</div><h2 id="count"></h2><h3>Notes</h3><div id="notes"></div><h3>Next</h3><div id="next"></div><script>let s=Date.now();setInterval(()=>{{let n=Math.floor((Date.now()-s)/1000);document.querySelector("#timer").textContent=String(Math.floor(n/60)).padStart(2,"0")+":"+String(n%60).padStart(2,"0")}},1000)<\\/script>');presenter.document.close();sync()}}addEventListener('resize',fit);addEventListener('keydown',e=>{{if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key))show(current+1);if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key))show(current-1);if(e.key==='Home')show(0);if(e.key==='End')show(slides.length-1);if(e.key.toLowerCase()==='f')document.documentElement.requestFullscreen?.();if(e.key.toLowerCase()==='s')openPresenter()}});fit();show(0);
</script></body></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(f"Created {output}\nSlides: {len(slides)}\nMode: fidelity-first rendered conversion")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        build_html(args.pptx.resolve(), args.output.resolve())
    except (OSError, RuntimeError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
