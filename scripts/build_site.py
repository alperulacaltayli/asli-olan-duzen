#!/usr/bin/env python3
"""Build the Asli Olan Duzen static site and discover archive nodes from folders."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_obsidian

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES_ROOT = ROOT / "content" / "archives"
DIST = ROOT / "dist"
TEXT_SUFFIXES = {".md", ".txt"}


def natural_key(value: str) -> list[Any]:
    # Type-tag each token so numeric and text segments remain comparable.
    return [(0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r"(\d+)", value)]


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def split_document(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    metadata: dict[str, Any] = {}

    if raw.startswith("---\n"):
        closing = raw.find("\n---", 4)
        if closing != -1:
            front_matter = raw[4:closing]
            raw = raw[closing + 4:].lstrip("\n")
            for line in front_matter.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                metadata[key.strip().lower()] = parse_scalar(value)

    lines = raw.splitlines()
    title = str(metadata.get("title", "")).strip()

    if not title and path.suffix.lower() == ".txt":
        first_nonempty = next((i for i, line in enumerate(lines) if line.strip()), None)
        if first_nonempty is not None:
            title = lines[first_nonempty].strip().lstrip("#").strip()
            lines = lines[:first_nonempty] + lines[first_nonempty + 1:]

    if not title:
        for index, line in enumerate(lines):
            match = re.match(r"^#\s+(.+)$", line.strip())
            if match:
                title = match.group(1).strip()
                lines.pop(index)
                break

    if not title:
        fallback = path.parent.name if path.name.lower() in {"index.md", "index.txt"} else path.stem
        title = re.sub(r"[-_]+", " ", fallback).strip().title()

    body = "\n".join(lines).strip()
    summary = str(metadata.get("summary", "")).strip()
    if not summary:
        for paragraph in re.split(r"\n\s*\n", body):
            candidate = re.sub(r"^#{1,6}\s+", "", paragraph.strip())
            candidate = re.sub(r"[*_\x60>#]", "", candidate).strip()
            if candidate:
                summary = candidate[:240]
                break

    return {
        "title": title,
        "date": str(metadata.get("date", "")).strip(),
        "summary": summary,
        "order": metadata.get("order", 999999),
        "content": body,
    }, body


def sort_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(node: dict[str, Any]) -> tuple[Any, ...]:
        order = node.get("order", 999999)
        try:
            order_key = int(order)
        except (TypeError, ValueError):
            order_key = 999999
        date = str(node.get("date", ""))
        date_key = natural_key(date) if date else natural_key(node["title"])
        return order_key, date_key, natural_key(node["title"])
    return sorted(nodes, key=key)


def build_node(file_path: Path, category_root: Path,
               child_dir: Path | None = None,
               exclude_child_file: Path | None = None) -> dict[str, Any]:
    metadata, _ = split_document(file_path)
    relative = file_path.relative_to(category_root).as_posix()
    node_id = relative.rsplit(".", 1)[0]

    children: list[dict[str, Any]] = []
    if child_dir and child_dir.is_dir():
        excluded = {exclude_child_file.resolve()} if exclude_child_file else set()
        children = scan_directory(child_dir, category_root, excluded)

    return {
        "id": node_id,
        "path": relative,
        "title": metadata["title"],
        "date": metadata["date"],
        "summary": metadata["summary"],
        "content": metadata["content"],
        "order": metadata["order"],
        "children": sort_nodes(children),
    }


def scan_directory(directory: Path, category_root: Path,
                   excluded: set[Path] | None = None) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []

    excluded = excluded or set()
    nodes: list[dict[str, Any]] = []
    paired_directories: set[Path] = set()
    entries = sorted(directory.iterdir(), key=lambda item: natural_key(item.name))

    # A file may have a sibling directory with the same name; that directory
    # becomes the file's child branch.
    for entry in entries:
        if not entry.is_file() or entry.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if entry.resolve() in excluded:
            continue
        paired = directory / entry.stem
        if paired.is_dir():
            paired_directories.add(paired.resolve())
        nodes.append(build_node(entry, category_root, paired if paired.is_dir() else None))

    # A directory with index.md/index.txt is one node. Its other files and
    # subdirectories become children. A directory without an index is a
    # grouping folder and its discovered nodes are promoted into this level.
    for entry in entries:
        if not entry.is_dir() or entry.resolve() in paired_directories:
            continue
        index_file = next(
            (entry / name for name in ("index.md", "index.txt") if (entry / name).is_file()),
            None,
        )
        if index_file:
            nodes.append(build_node(
                index_file, category_root, entry, exclude_child_file=index_file
            ))
        else:
            nodes.extend(scan_directory(entry, category_root))

    return sort_nodes(nodes)


def read_category(category_dir: Path) -> dict[str, Any]:
    config_path = category_dir / "_archive.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {
            "title": re.sub(r"[-_]+", " ", category_dir.name).title(),
            "description": "",
            "view": "tree",
            "label": "ARŞİV",
            "order": 999,
        }

    return {
        "id": category_dir.name,
        "title": config.get("title", category_dir.name.title()),
        "description": config.get("description", ""),
        "view": config.get("view", "tree"),
        "label": config.get("label", "ARŞİV"),
        "order": config.get("order", 999),
        "nodes": scan_directory(category_dir, category_dir),
    }


def discover_archives() -> dict[str, Any]:
    categories = []
    if ARCHIVES_ROOT.is_dir():
        for directory in sorted(ARCHIVES_ROOT.iterdir(), key=lambda p: natural_key(p.name)):
            if directory.is_dir() and not directory.name.startswith("_"):
                categories.append(read_category(directory))
    categories.sort(key=lambda item: (item.get("order", 999), item["title"].casefold()))
    return {"categories": categories}


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for filename in ("index.html", "robots.txt", "sitemap.xml"):
        source = ROOT / filename
        if source.is_file():
            shutil.copy2(source, DIST / filename)

    assets = ROOT / "assets"
    if assets.is_dir():
        shutil.copytree(assets, DIST / "assets")

    archive_data = import_obsidian.discover_archives()
    encoded = json.dumps(archive_data, ensure_ascii=False, indent=2) + "\n"

    # Keep a root copy for branch-based preview and place the deploy copy in dist.
    (ROOT / "archives.json").write_text(encoded, encoding="utf-8")
    (DIST / "archives.json").write_text(encoded, encoding="utf-8")

    print(f"Site built: {DIST}")
    print(f"Archive categories: {len(archive_data['categories'])}")
    for category in archive_data["categories"]:
        print(f" - {category['title']}: {len(category['nodes'])} top-level records")


if __name__ == "__main__":
    build()
