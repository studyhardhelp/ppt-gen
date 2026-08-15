#!/usr/bin/env python3
"""Discover and fetch vetted GitHub presentation-template sources."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import shutil
import subprocess
import sys
from pathlib import Path


REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "template-sources.json"


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
        items = [item for item in items if all(term in searchable(item) for term in terms)]
    return items


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
    for field, label in (
        ("by_route", "Routes"),
        ("by_kind", "Kinds"),
        ("by_license", "Licenses"),
    ):
        values = ", ".join(f"{key}={value}" for key, value in stats[field].items())
        print(f"{label}: {values}")


def clone(item: dict, destination: Path, timeout: int) -> str:
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
        result = subprocess.run(
            command, text=True, capture_output=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError(f"Clone timed out after {timeout} seconds") from exc
    if result.returncode != 0:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError((result.stderr or result.stdout).strip())
    commit = subprocess.run(
        [git, "-C", str(destination), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    return commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats_parser = subparsers.add_parser("stats", help="Summarize registry counts")
    stats_parser.add_argument("--json", action="store_true")

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

    args = parser.parse_args()
    data = load_registry()

    try:
        if args.command == "stats":
            stats = registry_stats(data)
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
            commit = clone(item, args.destination.resolve(), max(1, args.timeout))
            print(f"Cloned {item['repo']}")
            print(f"Commit: {commit}")
            print(f"Destination: {args.destination.resolve()}")
            print("Inspect the upstream README, AGENTS.md, code, assets, and license before use.")
    except (KeyError, FileExistsError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
