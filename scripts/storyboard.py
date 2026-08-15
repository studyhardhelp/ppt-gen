#!/usr/bin/env python3
"""Create a conservative presentation storyboard from normalized source material."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCENARIOS = {
    "executive": ["context", "evidence", "comparison", "process", "decision"],
    "consulting": ["argument", "evidence", "comparison", "process", "decision"],
    "pitch": ["context", "argument", "evidence", "comparison", "decision"],
    "academic": ["context", "evidence", "evidence", "argument", "close"],
    "teaching": ["context", "argument", "process", "evidence", "close"],
    "technical": ["context", "argument", "process", "comparison", "decision"],
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def shorten(value: str, limit: int) -> str:
    value = clean(value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."


def blocks(text: str) -> list[dict]:
    result = []
    current_title = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        body = clean(" ".join(current_lines))
        if body:
            sentences = [clean(item) for item in re.split(r"(?<=[.!?。！？；;])\s*|\n+", body) if clean(item)]
            result.append({"title": current_title, "sentences": sentences})
        current_lines = []

    for raw in text.splitlines():
        line = raw.strip()
        heading = re.match(r"^(?:#{1,6}\s+|\[Slide\s+\d+\]\s*)(.+)$", line, re.IGNORECASE)
        if heading:
            flush()
            current_title = clean(heading.group(1))
        elif not line:
            flush()
        else:
            current_lines.append(line.lstrip("-*+> "))
    flush()
    return result


def source_id(index: int) -> str:
    return f"S{index}"


def action_title(block: dict, fallback: str) -> str:
    title = block.get("title") or ""
    sentences = block.get("sentences") or []
    candidate = title if len(title) >= 8 else sentences[0] if sentences else title
    return shorten(candidate or fallback, 86)


def make_storyboard(ingested: dict, brief: dict, target: int, scenario: str) -> tuple[dict, str]:
    documents = ingested.get("documents") or []
    if not documents:
        raise ValueError("The ingestion file contains no documents")
    title = brief.get("title") or "Presentation"
    all_blocks = []
    tables = []
    ledger = ["# Source Ledger", "", "| ID | Publisher or owner | Title | Date | URL or local path | Used on slides |", "| --- | --- | --- | --- | --- | --- |"]
    for index, document in enumerate(documents, 1):
        sid = source_id(index)
        path = document.get("source", "")
        ledger.append(f"| {sid} | Source material | {Path(path).name if '://' not in path else path} |  | {path} | pending |")
        for block in blocks(document.get("text", "")):
            block["source_id"] = sid
            all_blocks.append(block)
        for table in document.get("tables") or []:
            if table:
                tables.append({"source_id": sid, "rows": table})
    if not all_blocks and not tables:
        raise ValueError("No usable text or tables were extracted")

    target = max(3, min(40, target))
    slides = [{"number": 1, "role": "cover", "action_title": title, "subtitle": brief.get("objective") or brief.get("subject") or "", "supporting_points": [], "source_ids": [], "speaker_note": ""}]
    body_budget = target - 2
    roles = SCENARIOS.get(scenario, SCENARIOS["executive"])
    block_index = 0
    table_index = 0
    for position in range(body_budget):
        role = roles[position % len(roles)]
        if table_index < len(tables) and (position == 1 or block_index >= len(all_blocks)):
            item = tables[table_index]
            table_index += 1
            rows = item["rows"]
            headers = rows[0] if rows else []
            slide = {"role": "evidence", "action_title": f"{title}: source data", "supporting_points": [], "table": {"headers": headers[:6], "rows": [row[:6] for row in rows[1:9]]}, "source_ids": [item["source_id"]], "speaker_note": "Confirm units, period, and methodology before presenting."}
        elif block_index < len(all_blocks):
            item = all_blocks[block_index]
            block_index += 1
            sentences = item.get("sentences") or []
            if role == "comparison" and len(sentences) < 3:
                role = "argument"
            if role == "process" and len(sentences) < 3:
                role = "content"
            slide = {"role": role, "action_title": action_title(item, f"{title}: key point"), "supporting_points": [shorten(sentence, 150) for sentence in sentences[1:5] or sentences[:4]], "visual": "", "source_ids": [item["source_id"]], "speaker_note": "Expand on the evidence without repeating the visible text."}
        else:
            break
        slide["number"] = len(slides) + 1
        slides.append(slide)
    slides.append({"number": len(slides) + 1, "role": "close", "action_title": brief.get("decision_or_action") or "Decision and next steps", "supporting_points": ["Confirm the decision, owner, and next review date."], "source_ids": [], "speaker_note": "Close with a specific decision or action."})
    used = {sid: [] for sid in (source_id(i) for i in range(1, len(documents) + 1))}
    for slide in slides:
        for sid in slide.get("source_ids", []):
            used.setdefault(sid, []).append(str(slide["number"]))
    for index in range(4, len(ledger)):
        sid = ledger[index].split("|", 2)[1].strip()
        ledger[index] = ledger[index].replace("pending |", f"{', '.join(used.get(sid, [])) or '-'} |")
    storyboard = {"deck": {"title": title, "subtitle": brief.get("objective", ""), "objective": brief.get("objective", ""), "audience": brief.get("audience", ""), "core_message": action_title(all_blocks[0], title) if all_blocks else title, "narrative": scenario}, "slides": slides}
    return storyboard, "\n".join(ledger) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ingested", type=Path)
    parser.add_argument("brief", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--slides", type=int, default=10)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="executive")
    args = parser.parse_args()
    try:
        ingested = json.loads(args.ingested.read_text(encoding="utf-8"))
        brief = json.loads(args.brief.read_text(encoding="utf-8"))
        storyboard, ledger = make_storyboard(ingested, brief, args.slides, args.scenario)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.sources:
        args.sources.parent.mkdir(parents=True, exist_ok=True)
        args.sources.write_text(ledger, encoding="utf-8")
    print(f"Created {args.output}\nSlides: {len(storyboard['slides'])}\nScenario: {args.scenario}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
