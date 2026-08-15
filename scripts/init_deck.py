#!/usr/bin/env python3
"""Create a clean working directory for a presentation project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


BRIEF = {
    "title": "",
    "objective": "",
    "audience": "",
    "decision_or_action": "",
    "duration_minutes": None,
    "target_slide_count": None,
    "language": "",
    "output_route": "native-pptx",
    "editability_required": True,
    "aspect_ratio": "16:9",
    "brand_or_template": None,
    "required_sections": [],
    "constraints": [],
    "theme": "executive",
    "author": "",
    "subject": "",
}


STORYBOARD = {
    "deck": {
        "title": "",
        "subtitle": "",
        "objective": "",
        "audience": "",
        "core_message": "",
        "narrative": "",
    },
    "slides": [
        {
            "number": 1,
            "role": "cover",
            "action_title": "",
            "supporting_points": [],
            "visual": "",
            "image": None,
            "metrics": [],
            "chart": None,
            "table": None,
            "columns": [],
            "source_ids": [],
            "speaker_note": "",
        }
    ],
}


SOURCES = """# Source Ledger

| ID | Publisher or owner | Title | Date | URL or local path | Used on slides |
| --- | --- | --- | --- | --- | --- |
"""

ROUTES = ("native-pptx", "template-pptx", "html", "image-first", "reconstruction")


def write_new(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --force")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Project directory to create")
    parser.add_argument("--title", default="", help="Initial deck title")
    parser.add_argument(
        "--route", choices=ROUTES, default="native-pptx", help="Output route"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite planning files")
    args = parser.parse_args()

    root = args.project.resolve()
    for directory in ("source", "assets", "work", "output"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    brief = dict(BRIEF)
    brief["title"] = args.title
    brief["output_route"] = args.route
    write_new(
        root / "work" / "brief.json",
        json.dumps(brief, indent=2, ensure_ascii=False) + "\n",
        args.force,
    )
    storyboard = json.loads(json.dumps(STORYBOARD))
    storyboard["deck"]["title"] = args.title
    write_new(
        root / "work" / "storyboard.json",
        json.dumps(storyboard, indent=2, ensure_ascii=False) + "\n",
        args.force,
    )
    write_new(root / "work" / "sources.md", SOURCES, args.force)
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
