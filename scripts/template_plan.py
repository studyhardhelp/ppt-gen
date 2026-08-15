#!/usr/bin/env python3
"""Map storyboard slides onto a profiled template and produce addressed edits."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pptx_check import PLACEHOLDER_RE


ROLE_HINTS = {
    "cover": ("cover", "title", "封面"),
    "section": ("section", "chapter", "目录", "章节"),
    "section_divider": ("section", "chapter", "章节"),
    "close": ("ending", "thanks", "thank you", "谢谢", "结束"),
    "comparison": ("compare", "versus", "对比"),
    "process": ("process", "timeline", "流程", "步骤"),
    "evidence": ("data", "chart", "数据", "图表"),
}


def text_slots(slide: dict) -> list[dict]:
    slots = []
    for shape in slide.get("shapes", []):
        for paragraph in shape.get("paragraphs", []):
            for run in paragraph.get("runs", []):
                raw_text = run.get("text", "")
                text = raw_text.strip()
                if text and not re.fullmatch(r"[\d\W_]+", text):
                    bounds = shape.get("bounds_emu") or {}
                    font = max(8, float(run.get("font_size_pt") or 18))
                    width_points = float(bounds.get("cx", 0)) / 12700
                    height_points = float(bounds.get("cy", 0)) / 12700
                    capacity = max(8, int((width_points / (font * 0.62)) * max(1.0, height_points / (font * 1.15)) * 0.7)) if width_points and height_points else max(8, len(text))
                    slots.append({"slot_id": run["slot_id"], "text": text, "expected_text": raw_text, "shape_id": shape.get("shape_id"), "kind": shape.get("kind"), "capacity": min(180, capacity), "font_size_pt": font, "x": float(bounds.get("x", 0)), "y": float(bounds.get("y", 0))})
    return slots


def score(template_slide: dict, role: str) -> int:
    text = template_slide.get("text", "").lower()
    shapes = template_slide.get("shapes", [])
    value = sum(4 for hint in ROLE_HINTS.get(role, ()) if hint in text)
    value += int(role == "cover" and template_slide["number"] == 1) * 6
    value += int(role == "close" and template_slide["number"] >= 0) * min(4, template_slide["number"] // 5)
    value += int(role == "evidence" and any(shape.get("chart_relationship_id") for shape in shapes)) * 5
    value += int(role == "evidence" and any(shape.get("is_table") for shape in shapes)) * 4
    value += int(role in {"content", "argument", "context", "decision", "result"} and 2 <= len(text_slots(template_slide)) <= 10) * 3
    if role not in {"cover", "section", "section_divider"} and re.search(r"\bcontents?\b|目录|章节", text):
        value -= 8
    if role not in {"cover", "section", "section_divider"} and template_slide["number"] <= 3:
        value -= 4
    return value


def fit(value: object, slot: dict, title: bool = False) -> tuple[str, float | None]:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    capacity = max(1, int(slot["capacity"]))
    original_size = float(slot.get("font_size_pt") or 18)
    if len(text) <= capacity:
        return text, None
    minimum_size = min(original_size, 22 if title else 11)
    desired_size = original_size * (capacity / max(1, len(text))) ** 0.5
    if desired_size >= minimum_size:
        return text, round(desired_size * 0.97, 1)
    fitted_capacity = int(capacity * (original_size / minimum_size) ** 2)
    fitted_text = text if len(text) <= fitted_capacity else text[: max(1, fitted_capacity - 3)].rstrip() + "..."
    return fitted_text, round(minimum_size, 1)


def ordered_slots(slots: list[dict]) -> list[dict]:
    if not slots:
        return []
    title = max(slots, key=lambda item: (item["font_size_pt"], item["capacity"], -item["y"], -item["x"]))
    remaining = [slot for slot in slots if slot is not title]
    remaining.sort(key=lambda item: (-item["capacity"], -item["font_size_pt"], item["y"], item["x"]))
    return [title, *remaining]


def choose(profile: dict, storyboard: dict) -> list[tuple[dict, dict]]:
    available = list(profile.get("slides", []))
    if len(available) < len(storyboard.get("slides", [])):
        raise ValueError("Template has fewer slides than the storyboard; reduce the storyboard or duplicate template layouts manually")
    mapping = []
    for story_slide in storyboard.get("slides", []):
        role = story_slide.get("role", "content")
        selected = max(available, key=lambda item: (score(item, role), -abs(item["number"] - story_slide.get("number", 1))))
        available.remove(selected)
        mapping.append((story_slide, selected))
    return mapping


def plan(profile: dict, storyboard: dict) -> dict:
    mapping = choose(profile, storyboard)
    edits = []
    selected = []
    audit = []
    for story, template in mapping:
        selected.append(template["number"])
        slots = ordered_slots(text_slots(template))
        visible = [story.get("action_title", "")]
        if story.get("role") == "cover" and story.get("subtitle"):
            visible.append(story["subtitle"])
        visible.extend(story.get("supporting_points") or [])
        for index, (slot, replacement) in enumerate(zip(slots, visible)):
            new_text, font_size = fit(replacement, slot, title=index == 0)
            edit = {"slide": template["number"], "slot_id": slot["slot_id"], "expected_text": slot["expected_text"], "new_text": new_text}
            if font_size is not None:
                edit["font_size_pt"] = font_size
            edits.append(edit)
        for slot in slots[len(visible) :]:
            protected = len(slot["text"]) <= 3 or re.search(r"原创|版权|copyright|稻壳|designer", slot["text"], re.IGNORECASE)
            if PLACEHOLDER_RE.search(slot["text"]) or not protected:
                edits.append({"slide": template["number"], "slot_id": slot["slot_id"], "expected_text": slot["expected_text"], "new_text": ""})
        audit.append({"storyboard_slide": story.get("number"), "role": story.get("role"), "template_slide": template["number"], "score": score(template, story.get("role", "content")), "filled_slots": min(len(slots), len(visible)), "available_slots": len(slots)})
    return {"schema": "ppt-template-edit/v2", "selected_slides": selected, "edits": edits, "mapping": audit}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("storyboard", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        storyboard = json.loads(args.storyboard.read_text(encoding="utf-8"))
        result = plan(profile, storyboard)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {args.output}\nMapped slides: {len(result['mapping'])}\nText edits: {len(result['edits'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
