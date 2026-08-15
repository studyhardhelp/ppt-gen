#!/usr/bin/env python3
"""Compare fonts referenced by a PPTX with fonts installed on the current system."""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

from pptx_check import inspect


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def installed_fonts() -> set[str]:
    fonts = set()
    fc_list = shutil.which("fc-list")
    if fc_list:
        result = subprocess.run([fc_list, ":", "family"], capture_output=True, text=True, check=False)
        for line in result.stdout.splitlines():
            fonts.update(name.strip() for name in line.split(",") if name.strip())
    elif platform.system() == "Darwin":
        for root in (Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"):
            if root.is_dir():
                fonts.update(path.stem for path in root.rglob("*") if path.suffix.lower() in {".ttf", ".otf", ".ttc", ".dfont"})
    return fonts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    referenced = inspect(args.pptx.resolve(), 10**9).get("fonts", [])
    installed = installed_fonts()
    normalized = {normalize(name) for name in installed}
    missing = [name for name in referenced if normalize(name) not in normalized and not any(normalize(name) in candidate or candidate in normalize(name) for candidate in normalized if candidate)]
    report = {"referenced": referenced, "installed_count": len(installed), "missing": missing}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Referenced fonts: {', '.join(referenced) or 'none'}")
        print(f"Missing fonts: {', '.join(missing) or 'none detected'}")
    return 2 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
