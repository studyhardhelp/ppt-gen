#!/usr/bin/env python3
"""Build a self-contained HTML presentation from a ppt-gen project."""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path


THEMES = {
    "executive": ("#f7f7f4", "#18202a", "#d9483b", "#2e6f73", "#65717c"),
    "boardroom": ("#f4f5f2", "#172126", "#b23a32", "#315f66", "#68747a"),
    "consulting": ("#ffffff", "#16212a", "#d81e34", "#296080", "#63717c"),
    "strategy": ("#f6f4ef", "#222222", "#b33a2e", "#315c53", "#6c6860"),
    "finance": ("#f6f8f7", "#14241f", "#147d64", "#c28b32", "#61716b"),
    "annual-report": ("#faf9f5", "#1c2328", "#9a3d35", "#3c6970", "#706d66"),
    "technical": ("#f4f7f8", "#13232c", "#00a39b", "#f0a202", "#5a6a72"),
    "terminal": ("#111714", "#ecf5ef", "#51d88a", "#e8bd61", "#9db1a4"),
    "blueprint": ("#f2f7fa", "#183446", "#177eaa", "#e76f51", "#637987"),
    "developer": ("#16191d", "#f1f3f5", "#6ee7b7", "#f59e0b", "#9ca3af"),
    "data": ("#f8fafb", "#17242c", "#00798c", "#edae49", "#687983"),
    "product": ("#fbfbfd", "#20212a", "#ff5a5f", "#00a699", "#747681"),
    "academic": ("#fbfaf7", "#20252b", "#8b1e3f", "#35605a", "#6b6f73"),
    "research": ("#f7f8f6", "#17211d", "#355c4f", "#a65f46", "#6b746f"),
    "thesis": ("#fffefb", "#252525", "#7a1f34", "#435d6b", "#6f6b66"),
    "journal": ("#f8f6f1", "#1d1d1b", "#b14934", "#2f5d62", "#6f6961"),
    "lecture": ("#fffdf7", "#24313a", "#e85d75", "#2a9d8f", "#66747c"),
    "science": ("#f6faf9", "#19302b", "#16817a", "#d66b3d", "#647872"),
    "editorial": ("#fcfbf8", "#151515", "#e4572e", "#2f6690", "#66625c"),
    "magazine": ("#fbfaf6", "#181818", "#d7263d", "#14746f", "#6e6960"),
    "newspaper": ("#f5f2ea", "#171717", "#a42424", "#365c6f", "#666058"),
    "minimal": ("#ffffff", "#191919", "#d1495b", "#267c7a", "#707070"),
    "mono": ("#f7f7f7", "#181818", "#555555", "#999999", "#686868"),
    "gallery": ("#faf9f6", "#1d1b1a", "#c94c32", "#396a68", "#6b6761"),
    "midnight": ("#12181d", "#f4f5f6", "#ffb703", "#2ec4b6", "#a9b4bc"),
    "charcoal": ("#1b1d1f", "#f3f1ed", "#e76f51", "#5bc0be", "#aaa8a3"),
    "neon": ("#101416", "#f5f7f7", "#00e0b8", "#ffca3a", "#a3b1b1"),
    "cinema": ("#151311", "#f5efe6", "#d85b3f", "#4f8a8b", "#b0a79d"),
    "education": ("#fffdf7", "#24313a", "#e85d75", "#2a9d8f", "#66747c"),
    "playful": ("#fffdf8", "#26313b", "#f2545b", "#00a8a8", "#66737c"),
    "workshop": ("#faf8f2", "#253039", "#ef8354", "#3c887e", "#6c746f"),
    "classroom": ("#fbfcf8", "#25322c", "#e56b6f", "#4f8f86", "#68736e"),
    "warm": ("#fffaf5", "#312b28", "#c8553d", "#588b8b", "#756c65"),
    "forest": ("#f5f8f4", "#1f3028", "#3d7a57", "#d28b45", "#67766d"),
    "ocean": ("#f3f8fa", "#173342", "#197b99", "#e67e50", "#637b87"),
    "culture": ("#fcf7f2", "#2e2521", "#b64b3c", "#34736d", "#766b65"),
}


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def embedded_image(project: Path, value: object) -> str | None:
    candidate = value if isinstance(value, str) else value.get("path") if isinstance(value, dict) else None
    if not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = project / path
    if not path.is_file():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render_chart(chart: dict) -> str:
    categories = chart.get("categories") or []
    series = (chart.get("series") or [])[:2]
    values = [float(value) for item in series for value in (item.get("values") or [])]
    if not categories or not series or not values:
        return ""
    maximum = max(values) or 1
    width, height, left, top = 900, 390, 70, 25
    plot_w, plot_h = 780, 285
    items = []
    for step in range(5):
        y = top + plot_h * step / 4
        items.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" class="grid"/>')
    colors = ("var(--accent)", "var(--accent2)")
    for series_index, item in enumerate(series):
        current = item.get("values") or []
        points = []
        for index, raw in enumerate(current[: len(categories)]):
            x = left + (plot_w * index / max(1, len(categories) - 1))
            y = top + plot_h - (float(raw) / maximum * plot_h)
            points.append((x, y, raw))
        items.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)}" fill="none" stroke="{colors[series_index]}" stroke-width="5"/>')
        items.extend(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{colors[series_index]}"/><text x="{x:.1f}" y="{y - 13:.1f}" text-anchor="middle">{esc(value)}</text>' for x, y, value in points)
    items.extend(f'<text x="{left + plot_w * index / max(1, len(categories) - 1):.1f}" y="350" text-anchor="middle">{esc(label)}</text>' for index, label in enumerate(categories))
    return f'<svg class="chart" viewBox="0 0 {width} {height}" role="img">{"".join(items)}</svg>'


def render_body(slide: dict, project: Path) -> str:
    points = slide.get("supporting_points") or []
    columns = slide.get("columns") or []
    metrics = slide.get("metrics") or []
    table = slide.get("table") or {}
    chart = slide.get("chart") or {}
    image = embedded_image(project, slide.get("image"))
    if chart:
        return render_chart(chart)
    if image:
        bullets = "<ul>" + "".join(f"<li>{esc(point if isinstance(point, str) else point.get('text'))}</li>" for point in points[:5]) + "</ul>"
        return f'<div class="media-layout">{bullets}<img src="{image}" alt="{esc(slide.get("image_alt") or slide.get("visual") or "Slide visual")}"></div>'
    if metrics:
        return '<div class="metrics">' + "".join(
            f'<div><strong>{esc(item.get("value", item.get("number", "")))}</strong><span>{esc(item.get("label", item.get("name", "")))}</span></div>'
            for item in metrics[:4]
        ) + "</div>"
    if columns:
        return '<div class="columns">' + "".join(
            f'<section><h2>{esc(column.get("title"))}</h2><ul>'
            + "".join(f"<li>{esc(point)}</li>" for point in column.get("points", []))
            + "</ul></section>" for column in columns[:3]
        ) + "</div>"
    if table.get("headers"):
        rows = [table["headers"], *(table.get("rows") or [])]
        return "<table>" + "".join(
            "<tr>" + "".join(("<th>" if i == 0 else "<td>") + esc(cell) + ("</th>" if i == 0 else "</td>") for cell in row) + "</tr>"
            for i, row in enumerate(rows[:11])
        ) + "</table>"
    return "<ul>" + "".join(f"<li>{esc(point if isinstance(point, str) else point.get('text'))}</li>" for point in points[:7]) + "</ul>"


def render_slide(slide: dict, index: int, deck: dict, project: Path) -> str:
    role = slide.get("role", "content")
    title = slide.get("action_title") or slide.get("title") or deck.get("title") or "Presentation"
    note = esc(slide.get("speaker_note"))
    sources = ", ".join(str(item) for item in slide.get("source_ids", []))
    if role == "cover":
        content = f'<h1>{esc(title)}</h1><p class="subtitle">{esc(slide.get("subtitle") or deck.get("subtitle") or deck.get("core_message"))}</p>'
    elif role in {"section", "section_divider"}:
        content = f'<p class="kicker">{index:02d}</p><h1>{esc(title)}</h1>'
    else:
        content = f'<h1>{esc(title)}</h1><div class="body">{render_body(slide, project)}</div>'
    footer = f'<footer><span>{esc(sources)}</span><span>{index:02d}</span></footer>'
    return f'<article class="slide role-{esc(role)}" data-index="{index - 1}">{content}{footer}<aside class="notes">{note}</aside></article>'


def build(project: Path, output: Path, theme_name: str | None) -> None:
    brief = json.loads((project / "work" / "brief.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project / "work" / "storyboard.json").read_text(encoding="utf-8"))
    slides = storyboard.get("slides") or []
    if not slides:
        raise ValueError("storyboard.slides must contain at least one slide")
    theme_name = theme_name or brief.get("theme") or "executive"
    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme {theme_name!r}; choose: {', '.join(THEMES)}")
    bg, ink, accent, accent2, muted = THEMES[theme_name]
    deck = storyboard.get("deck") or {}
    title = brief.get("title") or deck.get("title") or "Presentation"
    slide_html = "".join(render_slide(slide, index, deck, project) for index, slide in enumerate(slides, 1))
    theme_options = "".join(f'<option value="{esc(name)}">{esc(name)}</option>' for name in THEMES)
    theme_data = json.dumps(THEMES, ensure_ascii=True).replace("</", "<\\/")
    document = f'''<!doctype html>
<html lang="{esc(brief.get('language') or 'en')}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title><style>
:root{{--bg:{bg};--ink:{ink};--accent:{accent};--accent2:{accent2};--muted:{muted};--stage-w:1280px;--stage-h:720px}}
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#080b0d;color:var(--ink);font-family:Inter,"Noto Sans SC",system-ui,sans-serif;letter-spacing:0}}
#deck{{position:absolute;left:50%;top:50%;width:var(--stage-w);height:var(--stage-h);transform:translate(-50%,-50%) scale(var(--scale,1));transform-origin:center}}
.slide{{display:none;position:absolute;inset:0;padding:54px 68px;background:var(--bg);overflow:hidden}}.slide.active{{display:block}}
.slide h1{{margin:0;max-width:1120px;font-size:42px;line-height:1.14;letter-spacing:0}}.body{{margin-top:58px;height:500px;display:flex;align-items:center}}
.body>ul{{width:52%;margin:0;padding-left:32px;font-size:25px;line-height:1.42}}li{{margin:0 0 20px}}
.slide:not(.role-cover):not(.role-section):not(.role-section_divider)::before{{content:"";position:absolute;left:68px;top:31px;width:42px;height:4px;background:var(--accent)}}
.role-cover{{display:none;padding-top:160px;border-left:15px solid var(--accent)}}.role-cover h1,.role-section h1,.role-section_divider h1{{font-size:62px;max-width:1050px}}
.subtitle{{max-width:850px;margin-top:45px;font-size:28px;line-height:1.4;color:var(--muted)}}.role-section,.role-section_divider{{background:var(--accent);color:var(--bg);padding-top:190px}}
.kicker{{font-size:22px;font-weight:800}}footer{{position:absolute;left:68px;right:68px;bottom:25px;display:flex;justify-content:space-between;font-size:12px;color:var(--muted)}}
.columns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:38px;width:100%;align-self:stretch}}.columns section{{border-top:5px solid var(--accent);padding-top:20px}}.columns h2{{font-size:25px}}.columns ul{{font-size:19px;line-height:1.4;padding-left:25px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:25px;width:100%}}.metrics div{{text-align:center;border-top:5px solid var(--accent);padding-top:32px}}.metrics strong{{display:block;font-size:55px;color:var(--accent)}}.metrics span{{display:block;margin-top:15px;font-size:18px;color:var(--muted)}}
table{{border-collapse:collapse;width:100%;font-size:17px}}th,td{{padding:13px 15px;border-bottom:1px solid color-mix(in srgb,var(--muted) 35%,transparent);text-align:left}}th{{background:var(--accent);color:var(--bg)}}
.chart{{width:100%;height:100%;overflow:visible}}.chart text{{fill:var(--muted);font:16px system-ui,sans-serif}}.chart .grid{{stroke:var(--muted);stroke-opacity:.25;stroke-width:1}}.media-layout{{display:grid;grid-template-columns:1fr 1.05fr;gap:55px;width:100%;height:100%;align-items:center}}.media-layout ul{{font-size:23px;line-height:1.4}}.media-layout img{{width:100%;height:100%;object-fit:contain}}
.notes{{display:none}}#progress{{position:fixed;left:0;bottom:0;height:4px;background:var(--accent);transition:width .2s}}
#presenter{{display:none;position:fixed;inset:0;background:#111;color:#eee;padding:30px;z-index:5;grid-template-columns:2fr 1fr;gap:25px}}#presenter.open{{display:grid}}#presenter .preview{{background:#222;display:grid;place-items:center;font-size:38px}}#presenter .panel{{font-size:20px;line-height:1.5}}#timer{{font:700 44px ui-monospace,monospace;color:var(--accent)}}
#toolbar{{position:fixed;right:12px;top:12px;z-index:4;opacity:.12;transition:opacity .2s}}#toolbar:hover{{opacity:1}}select,button{{background:#161b1e;color:#fff;border:1px solid #53616a;padding:7px 9px}}
body.overview{{overflow:auto;background:#222}}body.overview #deck{{position:static;width:auto;height:auto;transform:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;padding:25px}}body.overview .slide{{display:block;position:relative;width:100%;aspect-ratio:16/9;transform:scale(.25);transform-origin:top left;margin-bottom:-75%;pointer-events:auto}}
@media print{{body{{overflow:visible;background:white}}#deck{{position:static;transform:none;width:1280px;height:auto}}.slide{{display:block;position:relative;width:1280px;height:720px;page-break-after:always}}#toolbar,#progress,#presenter{{display:none!important}}}}
</style></head><body><main id="deck">{slide_html}</main><div id="progress"></div>
<div id="toolbar"><select id="theme">{theme_options}</select><button id="fullscreen" title="Fullscreen">F</button></div>
<section id="presenter"><div class="preview" id="presenter-title"></div><div class="panel"><div id="timer">00:00</div><h2>Speaker notes</h2><div id="presenter-notes"></div></div></section>
<script>const themes={theme_data};let current=0,start=Date.now();const slides=[...document.querySelectorAll('.slide')],progress=document.querySelector('#progress');
function show(n){{current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>s.classList.toggle('active',i===current));progress.style.width=((current+1)/slides.length*100)+'%';updatePresenter()}}
function fit(){{document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720))}}function updatePresenter(){{document.querySelector('#presenter-title').textContent=slides[current].querySelector('h1')?.textContent||'';document.querySelector('#presenter-notes').textContent=slides[current].querySelector('.notes')?.textContent||'No speaker notes.'}}
function setTheme(name){{const t=themes[name];if(!t)return;['--bg','--ink','--accent','--accent2','--muted'].forEach((v,i)=>document.documentElement.style.setProperty(v,t[i]));localStorage.setItem('ppt-theme',name)}}
addEventListener('resize',fit);addEventListener('keydown',e=>{{if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key))show(current+1);if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key))show(current-1);if(e.key==='Home')show(0);if(e.key==='End')show(slides.length-1);if(e.key.toLowerCase()==='f')document.documentElement.requestFullscreen?.();if(e.key.toLowerCase()==='s')document.querySelector('#presenter').classList.toggle('open');if(e.key.toLowerCase()==='o')document.body.classList.toggle('overview')}});
setInterval(()=>{{const s=Math.floor((Date.now()-start)/1000);document.querySelector('#timer').textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}},1000);document.querySelector('#fullscreen').onclick=()=>document.documentElement.requestFullscreen?.();const picker=document.querySelector('#theme');picker.value=localStorage.getItem('ppt-theme')||'{theme_name}';picker.onchange=e=>setTheme(e.target.value);setTheme(picker.value);fit();show(0);</script></body></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(f"Created {output}\nSlides: {len(slides)}\nTheme: {theme_name}\nThemes available: {len(THEMES)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--theme")
    args = parser.parse_args()
    try:
        build(args.project.resolve(), args.output.resolve(), args.theme)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
