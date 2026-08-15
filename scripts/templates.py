#!/usr/bin/env python3
"""Discover and fetch vetted GitHub presentation-template sources."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import shutil
import subprocess
import sys
from pathlib import Path


REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "template-sources.json"
DEFAULT_LOCAL_ROOT = Path(__file__).resolve().parents[1] / "local-templates"


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def find_template(data: dict, template_id: str) -> dict:
    for item in data["templates"]:
        if item["id"] == template_id:
            return item
    raise KeyError(template_id)


def searchable(item: dict) -> str:
    values = [
        item["id"],
        item["name"],
        item["route"],
        item["kind"],
        item["license"],
        item["best_for"],
        *item.get("features", []),
    ]
    return " ".join(values).lower()


def select(data: dict, route: str | None, kind: str | None, query: str | None) -> list[dict]:
    items = data["templates"]
    if route:
        items = [item for item in items if item["route"] == route]
    if kind:
        items = [item for item in items if item["kind"] == kind]
    if query:
        terms = query.lower().split()
        scored = []
        for item in items:
            haystack = searchable(item)
            score = sum(haystack.count(term) * 2 + int(term in item["id"].lower()) * 3 + int(term in item["best_for"].lower()) for term in terms)
            if score:
                scored.append((score, item))
        items = [item for _, item in sorted(scored, key=lambda pair: (-pair[0], pair[1]["id"]))]
    return items


def github_request(url: str) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ppt-gen-skill"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_github(query: str, limit: int, licenses: set[str]) -> list[dict]:
    encoded = urllib.parse.quote(f"{query} in:name,description,readme")
    data = github_request(f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page={min(100, max(1, limit * 2))}")
    results = []
    for repository in data.get("items", []):
        relevance_text = " ".join([repository.get("name") or "", repository.get("description") or "", *(repository.get("topics") or [])]).lower()
        relevance = sum(relevance_text.count(term) for term in ("ppt", "pptx", "powerpoint", "presentation", "slide", "marp", "slidev"))
        if relevance < 4 or repository.get("name", "").lower().startswith("awesome-"):
            continue
        license_data = repository.get("license") or {}
        spdx = license_data.get("spdx_id")
        if not spdx or spdx == "NOASSERTION" or (licenses and spdx.lower() not in licenses):
            continue
        results.append({"repo": repository["full_name"], "url": repository["html_url"], "clone_url": repository["clone_url"], "description": repository.get("description") or "", "default_branch": repository.get("default_branch") or "main", "license": spdx, "stars": repository.get("stargazers_count", 0), "relevance": relevance, "topics": repository.get("topics") or []})
    return sorted(results, key=lambda item: (-item["relevance"], -item["stars"], item["repo"]))[:limit]


def print_table(items: list[dict]) -> None:
    if not items:
        print("No matching template sources")
        return
    widths = {
        "id": max(2, *(len(item["id"]) for item in items)),
        "route": max(5, *(len(item["route"]) for item in items)),
        "kind": max(4, *(len(item["kind"]) for item in items)),
    }
    print(
        f"{'ID':<{widths['id']}}  {'ROUTE':<{widths['route']}}  "
        f"{'KIND':<{widths['kind']}}  LICENSE  BEST FOR"
    )
    for item in items:
        print(
            f"{item['id']:<{widths['id']}}  {item['route']:<{widths['route']}}  "
            f"{item['kind']:<{widths['kind']}}  {item['license']:<7}  {item['best_for']}"
        )


def registry_stats(data: dict) -> dict:
    items = data["templates"]
    counts = Counter()
    for item in items:
        counts.update(item.get("counts", {}))

    return {
        "sources": len(items),
        "template_assets": counts["templates"] + counts["themes"],
        "templates": counts["templates"],
        "themes": counts["themes"],
        "layouts": counts["layouts"],
        "example_decks": counts["example_decks"],
        "by_route": dict(sorted(Counter(item["route"] for item in items).items())),
        "by_kind": dict(sorted(Counter(item["kind"] for item in items).items())),
        "by_license": dict(sorted(Counter(item["license"] for item in items).items())),
    }


def print_stats(stats: dict) -> None:
    print(f"Sources: {stats['sources']}")
    print(f"Templates/themes: {stats['template_assets']}")
    print(f"  Templates: {stats['templates']}")
    print(f"  Themes: {stats['themes']}")
    print(f"Layouts: {stats['layouts']}")
    print(f"Example decks: {stats['example_decks']}")
    if "local_templates" in stats:
        print(f"Local templates: {stats['local_templates']}")
    for field, label in (
        ("by_route", "Routes"),
        ("by_kind", "Kinds"),
        ("by_license", "Licenses"),
    ):
        values = ", ".join(f"{key}={value}" for key, value in stats[field].items())
        print(f"{label}: {values}")


def discover_local(root: Path) -> list[dict]:
    if not root.is_dir():
        return []
    items = []
    for template in sorted([*root.rglob("*.pptx"), *root.rglob("*.potx")]):
        directory = template.parent
        detail = directory / "detail.json"
        metadata = {}
        if detail.is_file():
            try:
                metadata = json.loads(detail.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {"metadata_error": "invalid detail.json"}
        preview = directory / "preview.png"
        items.append(
            {
                "name": metadata.get("name") or directory.name,
                "template": str(template.resolve()),
                "preview": str(preview.resolve()) if preview.is_file() else None,
                "detail": str(detail.resolve()) if detail.is_file() else None,
                "slide_count": metadata.get("slide_count"),
                "style": metadata.get("style"),
                "aspect": metadata.get("aspect"),
            }
        )
    return items


def write_local_gallery(items: list[dict], output: Path) -> None:
    cards = []
    for item in items:
        preview = item.get("preview")
        image = f'<img src="{html.escape(os.path.relpath(preview, output.parent))}" alt="{html.escape(item["name"])}">' if preview else '<div class="missing">No preview</div>'
        cards.append(f'<article>{image}<h2>{html.escape(item["name"])}</h2><p>{html.escape(str(item.get("style") or "Unclassified"))} | {html.escape(str(item.get("slide_count") or "?"))} slides</p><code>{html.escape(item["template"])}</code></article>')
    document = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Local PPT templates</title><style>
body{margin:0;background:#f3f4f5;color:#17202a;font:14px system-ui,sans-serif}header{padding:28px 4vw;background:#fff;border-bottom:1px solid #dfe3e6}h1{margin:0;font-size:26px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;padding:24px 4vw}article{background:#fff;border:1px solid #dfe3e6;padding:12px}img,.missing{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#e8eaec}.missing{display:grid;place-items:center;color:#79858c}h2{font-size:17px;margin:12px 0 4px}p{color:#66737a}code{display:block;overflow-wrap:anywhere;font-size:11px;color:#7a858b}
</style></head><body><header><h1>Local PPT templates</h1></header><main>""" + "".join(cards) + "</main></body></html>\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def git_run(command: list[str], timeout: int) -> str:
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Git command timed out after {timeout} seconds") from exc
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def source_manifest(item: dict, destination: Path, commit: str, timeout: int) -> dict:
    git = shutil.which("git")
    tree = git_run([git, "-C", str(destination), "rev-parse", "HEAD^{tree}"], timeout)
    licenses = sorted(path.name for path in destination.iterdir() if path.is_file() and path.name.lower().startswith(("license", "copying")))
    return {
        "schema": "ppt-gen-template-source/v1",
        "id": item["id"],
        "repository": item["repo"],
        "clone_url": item["clone_url"],
        "registered_ref": item["ref"],
        "commit": commit,
        "tree": tree,
        "registered_license": item["license"],
        "license_files": licenses,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def clone(item: dict, destination: Path, timeout: int, requested_commit: str | None = None) -> tuple[str, dict]:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("git is required to fetch template sources")
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        item["ref"],
        "--single-branch",
        item["clone_url"],
        str(destination),
    ]
    try:
        git_run(command, timeout)
        if requested_commit:
            git_run([git, "-C", str(destination), "fetch", "--depth", "1", "origin", requested_commit], timeout)
            git_run([git, "-C", str(destination), "checkout", "--detach", requested_commit], timeout)
    except RuntimeError:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    commit = git_run([git, "-C", str(destination), "rev-parse", "HEAD"], timeout)
    manifest = source_manifest(item, destination, commit, timeout)
    (destination / ".ppt-gen-source.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return commit, manifest


def verify_source(item: dict, destination: Path, timeout: int) -> dict:
    git = shutil.which("git")
    manifest_path = destination / ".ppt-gen-source.json"
    if not git or not manifest_path.is_file():
        raise RuntimeError("Fetched source manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    commit = git_run([git, "-C", str(destination), "rev-parse", "HEAD"], timeout)
    tree = git_run([git, "-C", str(destination), "rev-parse", "HEAD^{tree}"], timeout)
    dirty = bool(git_run([git, "-C", str(destination), "status", "--porcelain", "--untracked-files=no"], timeout))
    checks = {
        "registry_id": manifest.get("id") == item["id"],
        "repository": manifest.get("repository") == item["repo"],
        "commit": manifest.get("commit") == commit,
        "tree": manifest.get("tree") == tree,
        "license": manifest.get("registered_license") == item["license"],
        "license_files": bool(manifest.get("license_files")) and all((destination / name).is_file() for name in manifest.get("license_files", [])),
        "clean": not dirty,
    }
    return {"destination": str(destination), "commit": commit, "checks": checks, "valid": all(checks.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats_parser = subparsers.add_parser("stats", help="Summarize registry counts")
    stats_parser.add_argument("--json", action="store_true")
    stats_parser.add_argument("--include-local", action="store_true")
    stats_parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)

    list_parser = subparsers.add_parser("list", help="List template sources")
    list_parser.add_argument("--route")
    list_parser.add_argument("--kind")
    list_parser.add_argument("--json", action="store_true")

    search_parser = subparsers.add_parser("search", help="Search template metadata")
    search_parser.add_argument("query")
    search_parser.add_argument("--json", action="store_true")

    show_parser = subparsers.add_parser("show", help="Show one source")
    show_parser.add_argument("id")

    fetch_parser = subparsers.add_parser("fetch", help="Clone one source without running it")
    fetch_parser.add_argument("id")
    fetch_parser.add_argument("destination", type=Path)
    fetch_parser.add_argument("--timeout", type=int, default=120)
    fetch_parser.add_argument("--commit", help="Fetch and detach at an exact commit")

    verify_parser = subparsers.add_parser("verify", help="Verify a fetched source against its manifest")
    verify_parser.add_argument("id")
    verify_parser.add_argument("destination", type=Path)
    verify_parser.add_argument("--timeout", type=int, default=30)

    local_parser = subparsers.add_parser("local", help="List local PPTX/POTX templates")
    local_parser.add_argument("--root", type=Path, default=DEFAULT_LOCAL_ROOT)
    local_parser.add_argument("--json", action="store_true")
    local_parser.add_argument("--gallery", type=Path, help="Write an HTML preview gallery")

    discover_parser = subparsers.add_parser("discover", help="Discover explicitly licensed GitHub template repositories")
    discover_parser.add_argument("query", nargs="?", default="presentation template ppt pptx slides")
    discover_parser.add_argument("--limit", type=int, default=20)
    discover_parser.add_argument("--license", action="append", default=["mit", "apache-2.0", "cc0-1.0"], dest="licenses")
    discover_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    data = load_registry()

    try:
        if args.command == "stats":
            stats = registry_stats(data)
            if args.include_local:
                stats["local_templates"] = len(discover_local(args.local_root.resolve()))
            if args.json:
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            else:
                print_stats(stats)
        elif args.command == "list":
            items = select(data, args.route, args.kind, None)
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print_table(items)
        elif args.command == "search":
            items = select(data, None, None, args.query)
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print_table(items)
        elif args.command == "show":
            print(json.dumps(find_template(data, args.id), indent=2, ensure_ascii=False))
        elif args.command == "fetch":
            item = find_template(data, args.id)
            commit, manifest = clone(item, args.destination.resolve(), max(1, args.timeout), args.commit)
            print(f"Cloned {item['repo']}")
            print(f"Commit: {commit}")
            print(f"Tree: {manifest['tree']}")
            print(f"Destination: {args.destination.resolve()}")
            print("Inspect the upstream README, AGENTS.md, code, assets, and license before use.")
        elif args.command == "verify":
            item = find_template(data, args.id)
            report = verify_source(item, args.destination.resolve(), max(1, args.timeout))
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["valid"] else 2
        elif args.command == "local":
            items = discover_local(args.root.resolve())
            if args.gallery:
                write_local_gallery(items, args.gallery.resolve())
                print(f"Gallery: {args.gallery.resolve()}")
            if args.json:
                print(json.dumps(items, indent=2, ensure_ascii=False))
            else:
                print(f"Local templates: {len(items)}")
                for item in items:
                    print(f"- {item['name']} | {item.get('style') or 'unclassified'} | {item['template']}")
        elif args.command == "discover":
            items = discover_github(args.query, max(1, args.limit), {item.lower() for item in args.licenses})
            content = json.dumps(items, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                args.output.resolve().write_text(content, encoding="utf-8")
                print(f"Created {args.output.resolve()}")
            print(content, end="")
            print(f"Discovered: {len(items)}", file=sys.stderr)
    except (KeyError, FileExistsError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
