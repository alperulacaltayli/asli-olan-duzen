#!/usr/bin/env python3
"""Build the Asli Olan Duzen static site and discover archive nodes from folders."""

from __future__ import annotations

import json
import re
import mimetypes
import shutil
import unicodedata
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_obsidian

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES_ROOT = ROOT / "content" / "archives"
DIST = ROOT / "dist"
GALLERY_ROOT = ROOT / "AlternatifTarihfotoarşiv"
VIDEO_ROOT = ROOT / "VideoArsiv"
AUDIO_ROOT = ROOT / "Sesler"
AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".oga", ".m4a", ".aac", ".flac", ".opus"}
VIDEO_SUFFIXES = {".mp4", ".m4v", ".webm", ".ogv", ".ogg"}
VIDEO_POSTER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
GALLERY_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
GALLERY_EXCLUDED_TERMS = ("infaz",)
SITE_MATERIAL_FILES = [
    "KitapKapakFotosu.png",
    "OğuzKağanAtalayPosterÇizim.png",
    "Poster1.jpeg",
    "AmerikaHitlerAnkaraZiyaretHaberi.png",
    "DikeyTrİmpBayrak540x1920.png",
    "DikeyNaziİmpbayrak540x1920.png",
    "TürkİmpBayrak11ölçek.jpeg",
    "TrimpLogo.png",
]
GALLERY_TITLE_OVERRIDES = {
    "baküdüştü": "Bakü düştü",
    "beyazsaraytr": "Beyaz Saray · Washington, D.C.",
    "hitleratatürkziyareti": "Hitler'in Atatürk ziyareti",
    "kievdüşüş": "Kiev'in düşüşü",
    "leningraddüşüş": "Leningrad'ın düşüşü",
    "moskovadüşüş": "Moskova'nın düşüşü",
    "sevatipoolçıkarması": "Sevastopol çıkarması",
    "sivastipoldüşüş": "Sivastopol'un düşüşü",
    "stalinggraddüşüş": "Stalingrad'ın düşüşü",
    "türklerayda": "Türkler Ay'da",
}
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


def create_webp(source: Path, destination: Path) -> None:
    """Create a compressed WebP copy while preserving transparency and orientation."""
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if has_alpha else "RGB")
        image.save(destination, "WEBP", quality=82, method=6)


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
        "date": str(metadata.get("date", metadata.get("period", ""))).strip(),
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



def gallery_default_category(stem: str) -> str:
    key = unicodedata.normalize("NFKD", stem).casefold()
    key = "".join(char for char in key if not unicodedata.combining(char))
    if "ayda" in key:
        return "Uzay ve keşif"
    if "ataturkziyareti" in key or "beyazsaray" in key:
        return "Diplomasi ve şehirler"
    if "atom" in key:
        return "Bilim ve teknoloji"
    if any(term in key for term in ("dus", "cikarma", "baku")):
        return "Cephe kayıtları"
    return "Diğer kayıtlar"


def discover_gallery() -> dict[str, Any]:
    """Build a public image catalogue with optional human-authored metadata."""
    images: list[dict[str, Any]] = []
    if not GALLERY_ROOT.is_dir():
        return {"images": images}
    metadata_path = GALLERY_ROOT / "_metadata.json"
    metadata_catalog: dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata_catalog = payload.get("images", payload) if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            metadata_catalog = {}
    for image_path in sorted(GALLERY_ROOT.iterdir(), key=lambda item: natural_key(item.name)):
        if not image_path.is_file() or image_path.suffix.lower() not in GALLERY_SUFFIXES:
            continue
        normalized_stem = unicodedata.normalize("NFKD", image_path.stem).casefold()
        normalized_stem = "".join(char for char in normalized_stem if not unicodedata.combining(char))
        if any(term in normalized_stem for term in GALLERY_EXCLUDED_TERMS):
            continue
        stem_key = image_path.stem.casefold()
        title = GALLERY_TITLE_OVERRIDES.get(stem_key, re.sub(r"[_-]+", " ", image_path.stem).strip())
        metadata = metadata_catalog.get(image_path.name, {})
        if not isinstance(metadata, dict):
            metadata = {}
        date = str(metadata.get("date", "")).strip()
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date)
        images.append({
            "src": f"{GALLERY_ROOT.name}/{image_path.name}",
            "webp_src": f"{GALLERY_ROOT.name}/{image_path.stem}.webp",
            "title": str(metadata.get("title") or title),
            "number": len(images) + 1,
            "category": str(metadata.get("category") or gallery_default_category(image_path.stem)),
            "date": date,
            "year": int(year_match.group(1)) if year_match else None,
            "location": str(metadata.get("location", "")).strip(),
            "description": str(metadata.get("description", "")).strip(),
            "source": str(metadata.get("source", "")).strip(),
            "chronology": str(metadata.get("chronology", "")).strip(),
        })
    return {"images": images}



def discover_videos() -> dict[str, Any]:
    """Discover browser-playable videos and optional posters/metadata."""
    videos: list[dict[str, Any]] = []
    if not VIDEO_ROOT.is_dir():
        return {"videos": videos}

    metadata_path = VIDEO_ROOT / "_metadata.json"
    metadata_catalog: dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata_catalog = payload.get("videos", payload) if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            metadata_catalog = {}

    for video_path in sorted(VIDEO_ROOT.iterdir(), key=lambda item: natural_key(item.name)):
        if not video_path.is_file() or video_path.name.startswith("_") or video_path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        metadata = metadata_catalog.get(video_path.name, {})
        if not isinstance(metadata, dict):
            metadata = {}

        poster_name = str(metadata.get("poster", "")).strip()
        poster_path: Path | None = None
        if poster_name:
            candidate = VIDEO_ROOT / poster_name
            if Path(poster_name).name == poster_name and candidate.is_file() and candidate.suffix.lower() in VIDEO_POSTER_SUFFIXES:
                poster_path = candidate
        else:
            for suffix in (".webp", ".jpg", ".jpeg", ".png"):
                candidate = video_path.with_suffix(suffix)
                if candidate.is_file():
                    poster_path = candidate
                    break

        try:
            order = int(metadata.get("order", 999999))
        except (TypeError, ValueError):
            order = 999999

        guessed_type = mimetypes.guess_type(video_path.name)[0]
        if video_path.suffix.lower() in {".mp4", ".m4v"}:
            guessed_type = "video/mp4"
        elif video_path.suffix.lower() == ".webm":
            guessed_type = "video/webm"
        elif video_path.suffix.lower() in {".ogv", ".ogg"}:
            guessed_type = "video/ogg"

        videos.append({
            "src": f"{VIDEO_ROOT.name}/{video_path.name}",
            "file": video_path.name,
            "type": guessed_type or "application/octet-stream",
            "title": str(metadata.get("title") or re.sub(r"[-_]+", " ", video_path.stem).strip().title()),
            "date": str(metadata.get("date", "")).strip(),
            "category": str(metadata.get("category", "Video kayıtları")).strip(),
            "description": str(metadata.get("description", "")).strip(),
            "poster": f"{VIDEO_ROOT.name}/{poster_path.name}" if poster_path else "",
            "order": order,
        })

    videos.sort(key=lambda item: (item["order"], natural_key(item["file"])))
    for index, video in enumerate(videos, start=1):
        video["number"] = index
    return {"videos": videos}


def discover_audio() -> dict[str, Any]:
    """Discover audio records, preserving folder hierarchy and country ownership."""
    records: list[dict[str, Any]] = []
    if not AUDIO_ROOT.is_dir():
        return {"audio": records}

    metadata_path = AUDIO_ROOT / "_metadata.json"
    metadata_catalog: dict[str, Any] = {}
    if metadata_path.is_file():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata_catalog = payload.get("audio", payload) if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            metadata_catalog = {}

    def key_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).casefold()
        return "".join(char for char in normalized if not unicodedata.combining(char))

    for audio_path in sorted(AUDIO_ROOT.rglob("*"), key=lambda item: natural_key(item.as_posix())):
        if not audio_path.is_file() or audio_path.name.startswith("_") or audio_path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        relative = audio_path.relative_to(AUDIO_ROOT)
        relative_key = relative.as_posix()
        metadata = metadata_catalog.get(relative_key, metadata_catalog.get(audio_path.name, {}))
        if not isinstance(metadata, dict):
            metadata = {}

        country_hint = key_text(str(metadata.get("country", "")))
        path_hint = " ".join(key_text(part) for part in relative.parts[:-1])
        file_hint = key_text(audio_path.stem)
        if country_hint in {"german", "germany", "alman", "almanya", "de", "deutsch"}:
            country = "german"
        elif country_hint in {"turkish", "turkey", "turk", "turkiye", "tr"}:
            country = "turkish"
        elif any(term in path_hint or term in file_hint for term in ("alman", "almanya", "germany", "german", "deutsch", "reich")):
            country = "german"
        elif any(term in path_hint or term in file_hint for term in ("turk", "turkiye", "turkish")):
            country = "turkish"
        else:
            country = "unassigned"

        category = str(metadata.get("category") or (relative.parts[0] if len(relative.parts) > 1 else "Diğer Sesler")).strip()
        subcategory = str(metadata.get("subcategory") or (relative.parts[1] if len(relative.parts) > 2 else "")).strip()
        category_key = key_text(category)
        archive_type = key_text(str(metadata.get("archive_type", "")))
        if archive_type not in {"state", "marches", "sounds"}:
            if any(term in category_key for term in ("devlet", "resmi", "official", "state")):
                archive_type = "state"
            elif "mars" in category_key:
                archive_type = "marches"
            else:
                archive_type = "sounds"
        try:
            order = int(metadata.get("order", 999999))
        except (TypeError, ValueError):
            order = 999999

        suffix = audio_path.suffix.lower()
        audio_type = {
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
            ".oga": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
            ".flac": "audio/flac", ".opus": "audio/opus",
        }.get(suffix, mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream")
        fallback_title = re.sub(r"[-_]+", " ", audio_path.stem).strip()
        record = {
            "src": f"{AUDIO_ROOT.name}/{relative.as_posix()}",
            "file": audio_path.name,
            "title": str(metadata.get("title") or fallback_title),
            "country": country,
            "category": category,
            "subcategory": subcategory,
            "archive_type": archive_type,
            "date": str(metadata.get("date", "")).strip(),
            "description": str(metadata.get("description", "")).strip(),
            "type": audio_type,
            "order": order,
        }

        # Optional text fields let songs carry lyrics and spoken records carry transcripts.
        for field in ("lyrics", "transcript", "performer", "composer", "lyricist", "credits", "language"):
            value = metadata.get(field)
            if isinstance(value, list):
                value = "\n".join(str(part) for part in value)
            if value is not None and str(value).strip():
                record[field] = str(value).strip()
        records.append(record)

    country_order = {"turkish": 0, "german": 1, "unassigned": 2}
    records.sort(key=lambda item: (country_order.get(item["country"], 9), item["order"], natural_key(item["src"])))
    for index, record in enumerate(records, start=1):
        record["number"] = index
    return {"audio": records}


def build() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for filename in ("index.html", "galeri.html", "sesler.html", "dosya-merkezi.html", "required-files.json", "404.html", "robots.txt", "sitemap.xml"):
        source = ROOT / filename
        if source.is_file():
            shutil.copy2(source, DIST / filename)

    template_source = ROOT / "GerekliDosyalar"
    if template_source.is_dir():
        shutil.copytree(template_source, DIST / "GerekliDosyalar")

    assets = ROOT / "assets"
    if assets.is_dir():
        shutil.copytree(assets, DIST / "assets")

    material_source = ROOT / "SiteMalzemeleri"
    material_target = DIST / "SiteMalzemeleri"
    for collection in ("NaziSiteMalzemeler", "TürkSiteMalzemeler"):
        source_collection = material_source / collection
        if source_collection.is_dir():
            shutil.copytree(source_collection, material_target / collection, dirs_exist_ok=True)
    for filename in SITE_MATERIAL_FILES:
        source = material_source / filename
        if source.is_file():
            material_target.mkdir(parents=True, exist_ok=True)
            destination = material_target / filename
            shutil.copy2(source, destination)
            create_webp(destination, destination.with_suffix(".webp"))

    gallery_data = discover_gallery()
    gallery_encoded = json.dumps(gallery_data, ensure_ascii=False, indent=2) + "\n"
    (ROOT / "gallery.json").write_text(gallery_encoded, encoding="utf-8")
    (DIST / "gallery.json").write_text(gallery_encoded, encoding="utf-8")

    # Copy only the images included in the public gallery catalogue.
    for image in gallery_data["images"]:
        source = ROOT / image["src"]
        destination = DIST / image["src"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        create_webp(destination, destination.with_suffix(".webp"))

    video_data = discover_videos()
    video_encoded = json.dumps(video_data, ensure_ascii=False, indent=2) + "\n"
    (ROOT / "videos.json").write_text(video_encoded, encoding="utf-8")
    (DIST / "videos.json").write_text(video_encoded, encoding="utf-8")
    for video in video_data["videos"]:
        source = ROOT / video["src"]
        destination = DIST / video["src"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if video["poster"]:
            poster_source = ROOT / video["poster"]
            poster_destination = DIST / video["poster"]
            poster_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(poster_source, poster_destination)

    audio_data = discover_audio()
    audio_encoded = json.dumps(audio_data, ensure_ascii=False, indent=2) + "\n"
    (ROOT / "audio.json").write_text(audio_encoded, encoding="utf-8")
    (DIST / "audio.json").write_text(audio_encoded, encoding="utf-8")
    for item in audio_data["audio"]:
        source = ROOT / item["src"]
        destination = DIST / item["src"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    archive_data = import_obsidian.discover_archives()
    encoded = json.dumps(archive_data, ensure_ascii=False, indent=2) + "\n"

    # Keep a root copy for branch-based preview and place the deploy copy in dist.
    (ROOT / "archives.json").write_text(encoded, encoding="utf-8")
    (DIST / "archives.json").write_text(encoded, encoding="utf-8")

    # Embed the same archive payload in index.html so the public archive does
    # not depend on a second HTTP request succeeding before categories render.
    index_path = DIST / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    main_script_marker = '<script src="assets/js/main.js?'
    if main_script_marker not in index_html:
        raise RuntimeError("index.html içinde main.js bağlantısı bulunamadı.")
    inline_archive_json = json.dumps(archive_data, ensure_ascii=False, separators=(",", ":"))
    # Escape closing-script sequences so text inside the JSON cannot terminate
    # the application/json script element during HTML parsing.
    inline_archive_json = inline_archive_json.replace("</", "<\\/")
    archive_data_script = (
        '<script type="application/json" id="archive-data">'
        + inline_archive_json
        + "</script>\n  "
    )
    index_html = index_html.replace(main_script_marker, archive_data_script + main_script_marker, 1)
    index_path.write_text(index_html, encoding="utf-8")

    print(f"Embedded archive data: {len(archive_data['categories'])} categories")
    print(f"Site built: {DIST}")
    print(f"Gallery images: {len(gallery_data['images'])}")
    print(f"Archive categories: {len(archive_data['categories'])}")
    for category in archive_data["categories"]:
        print(f" - {category['title']}: {len(category['nodes'])} top-level records")


if __name__ == "__main__":
    build()
