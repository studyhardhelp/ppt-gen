#!/usr/bin/env python3
"""Unified command-line entry point for the ppt-gen skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run(command: list[str], *, env: dict[str, str] | None = None) -> int:
    print("+ " + " ".join(str(part) for part in command))
    return subprocess.run(command, env=env, check=False).returncode


def load_brief(project: Path) -> dict:
    path = project / "work" / "brief.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing project brief: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def native_command(project: Path, output: Path, theme: str | None) -> tuple[list[str], dict[str, str]]:
    from doctor import build_report

    report = build_report()
    tools = report["tools"]
    if not report["capabilities"]["native_pptx_generation"]:
        raise RuntimeError("PptxGenJS is unavailable; run scripts/doctor.py for details")
    command = [tools["node"], str(SCRIPT_DIR / "build_pptx.cjs"), str(project), str(output)]
    if theme:
        command.extend(["--theme", theme])
    env = os.environ.copy()
    if tools.get("node_path"):
        env["NODE_PATH"] = tools["node_path"]
    return command, env


def build(args: argparse.Namespace) -> int:
    project = args.project.resolve()
    brief = load_brief(project)
    route = args.route or brief.get("output_route", "native-pptx")
    suffix = ".html" if route == "html" else ".pptx"
    output = (args.output or project / "output" / f"deck{suffix}").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if route == "native-pptx":
        command, env = native_command(project, output, args.theme or brief.get("theme"))
        code = run(command, env=env)
    elif route == "html":
        command = [sys.executable, str(SCRIPT_DIR / "build_html.py"), str(project), str(output)]
        if args.theme:
            command.extend(["--theme", args.theme])
        code = run(command)
    elif route == "template-pptx":
        if not args.template or not args.edits:
            raise RuntimeError("template-pptx requires --template and --edits")
        command = [sys.executable, str(SCRIPT_DIR / "pptx_edit.py"), str(args.template.resolve()), str(args.edits.resolve()), str(output), "--strict"]
        if args.profile:
            command.extend(["--profile", str(args.profile.resolve())])
        code = run(command)
    elif route == "image-first":
        if not args.images and not args.manifest:
            raise RuntimeError("image-first requires --images or --manifest")
        from doctor import build_report

        report = build_report()
        if not report["capabilities"]["native_pptx_generation"]:
            raise RuntimeError("PptxGenJS is unavailable")
        image_root = args.images.resolve() if args.images else args.manifest.resolve().parent
        command = [report["tools"]["node"], str(SCRIPT_DIR / "images_to_pptx.cjs"), str(image_root), str(output), "--aspect-ratio", brief.get("aspect_ratio", "16:9")]
        if args.manifest:
            command.extend(["--manifest", str(args.manifest.resolve())])
        env = os.environ.copy()
        if report["tools"].get("node_path"):
            env["NODE_PATH"] = report["tools"]["node_path"]
        code = run(command, env=env)
    elif route == "reconstruction":
        if not args.source:
            raise RuntimeError("reconstruction requires --source")
        command = [sys.executable, str(SCRIPT_DIR / "reconstruct.py"), str(args.source.resolve()), str(output)]
        if args.language:
            command.extend(["--language", args.language])
        command.extend(["--aspect-ratio", brief.get("aspect_ratio", "16:9")])
        code = run(command)
    else:
        raise RuntimeError(f"Unsupported route: {route}")

    if code != 0 or suffix != ".pptx" or args.skip_check:
        return code
    code = run([sys.executable, str(SCRIPT_DIR / "pptx_check.py"), str(output)])
    if code == 0 and args.render:
        code = run([sys.executable, str(SCRIPT_DIR / "render_deck.py"), str(output), "--output-dir", str(project / "work" / "rendered"), "--clean"])
    return code


def passthrough(script: str, values: list[str]) -> int:
    return run([sys.executable, str(SCRIPT_DIR / script), *values])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a project workspace")
    init.add_argument("project", type=Path)
    init.add_argument("--title", default="")
    init.add_argument("--route", default="native-pptx")
    init.add_argument("--aspect-ratio", default="16:9")
    init.add_argument("--force", action="store_true")
    create = sub.add_parser("create", help="Create a complete deck directly from source material")
    create.add_argument("project", type=Path)
    create.add_argument("inputs", nargs="+")
    create.add_argument("--title", required=True)
    create.add_argument("--route", default="native-pptx")
    create.add_argument("--theme", default="executive")
    create.add_argument("--aspect-ratio", default="16:9")
    create.add_argument("--slides", type=int, default=10)
    create.add_argument("--scenario", default="executive")
    create.add_argument("--render", action="store_true")
    create.add_argument("--force", action="store_true")
    build_parser = sub.add_parser("build", help="Build a deck from a project")
    build_parser.add_argument("project", type=Path)
    build_parser.add_argument("--route")
    build_parser.add_argument("--output", type=Path)
    build_parser.add_argument("--theme")
    build_parser.add_argument("--template", type=Path)
    build_parser.add_argument("--edits", type=Path)
    build_parser.add_argument("--profile", type=Path)
    build_parser.add_argument("--images", type=Path)
    build_parser.add_argument("--manifest", type=Path)
    build_parser.add_argument("--source", type=Path)
    build_parser.add_argument("--language")
    build_parser.add_argument("--render", action="store_true")
    build_parser.add_argument("--skip-check", action="store_true")
    qa = sub.add_parser("qa", help="Check and render a PPTX")
    qa.add_argument("pptx", type=Path)
    qa.add_argument("--output-dir", type=Path)
    qa.add_argument("--strict", action="store_true")
    qa.add_argument("--baseline", type=Path)
    qa.add_argument("--check-fonts", action="store_true")
    convert = sub.add_parser("convert", help="Convert PPTX to HTML/PDF or HTML to PDF/PPTX")
    convert.add_argument("source", type=Path)
    convert.add_argument("output", type=Path)
    ingest = sub.add_parser("ingest", help="Extract normalized content from source files or URLs")
    ingest.add_argument("inputs", nargs="+")
    ingest.add_argument("--output", type=Path, required=True)
    profile = sub.add_parser("profile-template", help="Inspect a PPTX/POTX template")
    profile.add_argument("template", type=Path)
    profile.add_argument("--output", type=Path)
    template_plan = sub.add_parser("template-plan", help="Map a storyboard onto a template profile")
    template_plan.add_argument("profile", type=Path)
    template_plan.add_argument("storyboard", type=Path)
    template_plan.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "init":
            values = [str(args.project), "--title", args.title, "--route", args.route, "--aspect-ratio", args.aspect_ratio]
            if args.force:
                values.append("--force")
            return passthrough("init_deck.py", values)
        if args.command == "create":
            project = args.project.resolve()
            values = [str(project), "--title", args.title, "--route", args.route, "--aspect-ratio", args.aspect_ratio]
            if args.force:
                values.append("--force")
            code = passthrough("init_deck.py", values)
            if code:
                return code
            brief_path = project / "work" / "brief.json"
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            brief["theme"] = args.theme
            brief["target_slide_count"] = args.slides
            brief_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            ingested = project / "work" / "ingested.json"
            code = passthrough("ingest.py", [*args.inputs, "--output", str(ingested)])
            if code:
                return code
            code = passthrough("storyboard.py", [str(ingested), str(brief_path), str(project / "work" / "storyboard.json"), "--sources", str(project / "work" / "sources.md"), "--slides", str(args.slides), "--scenario", args.scenario])
            if code:
                return code
            return build(argparse.Namespace(project=project, route=args.route, output=None, theme=args.theme, template=None, edits=None, profile=None, images=None, manifest=None, source=None, language=None, render=args.render, skip_check=False))
        if args.command == "build":
            return build(args)
        if args.command == "ingest":
            return passthrough("ingest.py", [*args.inputs, "--output", str(args.output)])
        if args.command == "profile-template":
            values = [str(args.template)]
            if args.output:
                values.extend(["--output", str(args.output)])
            return passthrough("template_profile.py", values)
        if args.command == "template-plan":
            return passthrough("template_plan.py", [str(args.profile), str(args.storyboard), str(args.output)])
        if args.command == "qa":
            check_values = [str(args.pptx)] + (["--strict"] if args.strict else [])
            code = passthrough("pptx_check.py", check_values)
            if code:
                return code
            if args.check_fonts:
                code = passthrough("font_check.py", [str(args.pptx)])
                if code:
                    return code
            output = args.output_dir or args.pptx.parent / f"{args.pptx.stem}-rendered"
            code = passthrough("render_deck.py", [str(args.pptx), "--output-dir", str(output), "--clean"])
            if code == 0 and args.baseline:
                code = passthrough("compare_renders.py", [str(args.baseline), str(output)])
            return code
        if args.command == "convert":
            source, output = args.source.resolve(), args.output.resolve()
            pair = (source.suffix.lower(), output.suffix.lower())
            if pair == (".pptx", ".html"):
                return passthrough("pptx_to_html.py", [str(source), str(output)])
            if pair == (".html", ".pptx"):
                return passthrough("html_to_pptx.py", [str(source), str(output)])
            if pair == (".html", ".pdf"):
                from doctor import build_report

                report = build_report(); tools = report["tools"]
                if not report["capabilities"].get("html_export"):
                    raise RuntimeError("Playwright/Chromium is unavailable")
                env = os.environ.copy()
                if tools.get("playwright_node_path"):
                    env["NODE_PATH"] = tools["playwright_node_path"]
                return run([tools["playwright_node"], str(SCRIPT_DIR / "html_export.cjs"), str(source), "pdf", str(output)], env=env)
            if pair == (".pptx", ".pdf"):
                with tempfile.TemporaryDirectory(prefix="pptx-to-pdf-") as directory:
                    code = passthrough("render_deck.py", [str(source), "--output-dir", directory, "--clean"])
                    if code:
                        return code
                    generated = Path(directory) / f"{source.stem}.pdf"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(generated, output)
                    print(f"Created {output}")
                    return 0
            raise RuntimeError(f"Unsupported conversion: {source.suffix} -> {output.suffix}")
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
