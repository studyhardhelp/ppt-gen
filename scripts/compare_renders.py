#!/usr/bin/env python3
"""Compare two directories of rendered slides and optionally write visual diffs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def slide_number(path: Path) -> int:
    match = re.search(r"(\d+)$", path.stem)
    return int(match.group(1)) if match else 0


def images(directory: Path) -> list[Path]:
    return sorted((path for path in directory.glob("slide-*.png")), key=slide_number)


def compare(baseline: Path, candidate: Path, diff_dir: Path | None = None) -> dict:
    from PIL import Image, ImageChops, ImageStat

    left, right = images(baseline), images(candidate)
    report = {"schema": "ppt-render-comparison/v1", "baseline": str(baseline), "candidate": str(candidate), "slide_count_match": len(left) == len(right), "slides": []}
    if diff_dir:
        diff_dir.mkdir(parents=True, exist_ok=True)
    for index in range(max(len(left), len(right))):
        if index >= len(left) or index >= len(right):
            report["slides"].append({"number": index + 1, "status": "missing", "baseline": str(left[index]) if index < len(left) else None, "candidate": str(right[index]) if index < len(right) else None})
            continue
        baseline_image = Image.open(left[index]).convert("RGB")
        candidate_image = Image.open(right[index]).convert("RGB")
        if candidate_image.size != baseline_image.size:
            candidate_image = candidate_image.resize(baseline_image.size)
        difference = ImageChops.difference(baseline_image, candidate_image)
        stat = ImageStat.Stat(difference)
        rms = sum(value * value for value in stat.rms) ** 0.5 / (3 ** 0.5)
        histogram = difference.convert("L").histogram()
        changed = sum(histogram[3:]) / max(1, baseline_image.width * baseline_image.height)
        item = {"number": index + 1, "status": "same" if changed == 0 else "changed", "rms": round(rms, 3), "changed_pixel_ratio": round(changed, 6)}
        if diff_dir and changed:
            output = diff_dir / f"diff-{index + 1:02d}.png"
            difference.save(output)
            item["diff"] = str(output)
        report["slides"].append(item)
    report["identical"] = report["slide_count_match"] and all(slide.get("status") == "same" for slide in report["slides"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--diff-dir", type=Path)
    parser.add_argument("--json", type=Path, dest="json_output")
    parser.add_argument("--max-changed", type=float, default=1.0, help="Fail if any changed-pixel ratio exceeds this value")
    args = parser.parse_args()
    try:
        report = compare(args.baseline.resolve(), args.candidate.resolve(), args.diff_dir.resolve() if args.diff_dir else None)
    except (ImportError, OSError, ValueError) as exc:
        parser.error(str(exc))
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.resolve().write_text(content, encoding="utf-8")
    print(content, end="")
    worst = max((slide.get("changed_pixel_ratio", 1.0) for slide in report["slides"]), default=0.0)
    return 2 if not report["slide_count_match"] or worst > args.max_changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
