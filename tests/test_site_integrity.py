from __future__ import annotations

import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "galeri.html", "sesler.html", "dosya-merkezi.html", "404.html")
VAULT = ROOT / "AslıOlanDüzenObsidianVault"
sys.path.insert(0, str(ROOT / "scripts"))
import import_obsidian  # noqa: E402


class PageReferences(HTMLParser):
    """Collect local page resources and fragment targets without a third-party parser."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        for name in ("href", "src", "poster", "action"):
            value = values.get(name)
            if value:
                self.references.append((name, value))
        srcset = values.get("srcset")
        if srcset:
            for candidate in srcset.split(","):
                resource = candidate.strip().split()
                if resource:
                    self.references.append(("srcset", resource[0]))


def resolve_local_reference(reference: str) -> tuple[Path | None, str]:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//"):
        return None, parsed.fragment
    path = unquote(parsed.path)
    if not path:
        return None, parsed.fragment
    return ROOT / path.lstrip("/"), parsed.fragment


def generated_webp_has_source(path: Path) -> bool:
    if path.is_file():
        return True
    if path.suffix.lower() != ".webp":
        return False
    return any(path.with_suffix(ext).is_file() for ext in (".png", ".jpg", ".jpeg"))


class SiteIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages: dict[str, PageReferences] = {}
        for page in PAGES:
            path = ROOT / page
            if path.is_file():
                parser = PageReferences()
                parser.feed(path.read_text(encoding="utf-8"))
                cls.pages[page] = parser

    def test_all_public_pages_exist_and_have_local_resources(self) -> None:
        self.assertEqual(set(self.pages), set(PAGES))
        for page, parser in self.pages.items():
            for kind, reference in parser.references:
                with self.subTest(page=page, kind=kind, reference=reference):
                    target, fragment = resolve_local_reference(reference)
                    if target is None:
                        if fragment:
                            self.assertIn(fragment, parser.ids, f"Bozuk sayfa içi bağlantı: {page}#{fragment}")
                        continue
                    self.assertTrue(
                        generated_webp_has_source(target),
                        f"{page} içindeki {kind} dosyası bulunamadı: {reference}",
                    )
                    if fragment and target.suffix.lower() == ".html" and target.name in self.pages:
                        self.assertIn(fragment, self.pages[target.name].ids, f"Bozuk sayfa bağlantısı: {reference}")

    def test_stylesheets_have_no_missing_local_url_assets(self) -> None:
        for stylesheet in (ROOT / "assets" / "css").glob("*.css"):
            content = stylesheet.read_text(encoding="utf-8")
            for match in re.finditer(r"url\(\s*[\"']?([^\"')]+)[\"']?\s*\)", content, re.I):
                reference = match.group(1).strip()
                parsed = urlsplit(reference)
                if parsed.scheme or parsed.netloc or reference.startswith("//"):
                    continue
                target = stylesheet.parent / unquote(parsed.path)
                with self.subTest(stylesheet=str(stylesheet.relative_to(ROOT)), reference=reference):
                    self.assertTrue(
                        generated_webp_has_source(target),
                        f"CSS dosyasında bulunamayan kaynak: {reference}",
                    )

    def test_published_media_manifests_point_to_existing_source_files(self) -> None:
        manifests = (
            ("gallery.json", "images", ("src",)),
            ("videos.json", "videos", ("src", "poster")),
            ("audio.json", "audio", ("src",)),
        )
        for filename, collection, fields in manifests:
            payload = json.loads((ROOT / filename).read_text(encoding="utf-8"))
            for record in payload.get(collection, []):
                for field in fields:
                    reference = record.get(field)
                    if not reference:
                        continue
                    with self.subTest(manifest=filename, record=record.get("title"), field=field):
                        self.assertTrue(
                            (ROOT / reference).is_file(),
                            f"{filename} içinde kaynak dosya bulunamadı: {reference}",
                        )
                if filename == "gallery.json":
                    webp = record.get("webp_src")
                    if webp:
                        with self.subTest(manifest=filename, record=record.get("title"), field="webp_src"):
                            self.assertTrue(
                                generated_webp_has_source(ROOT / webp),
                                f"WebP çıktısı için kaynak görsel bulunamadı: {webp}",
                            )

    def test_published_archive_records_have_source_documents(self) -> None:
        # Validate the archive generated from the current importer, not the
        # checked-in JSON snapshot that the Pages workflow refreshes later.
        payload = import_obsidian.discover_archives()
        def visit(category_id: str, nodes: list[dict]) -> None:
            for node in nodes:
                reference = str(node.get("sourceFile") or node.get("path", ""))
                if reference.lower().endswith((".md", ".txt", ".json")):
                    candidates = (
                        ROOT / reference,
                        VAULT / reference,
                        ROOT / "content" / "archives" / category_id / reference,
                    )
                    self.assertTrue(
                        any(candidate.is_file() for candidate in candidates),
                        f"Yayındaki arşiv kaydının kaynak dosyası bulunamadı: {category_id}/{reference}",
                    )
                visit(category_id, node.get("children", []))
        for category in payload.get("categories", []):
            with self.subTest(category=category.get("id")):
                visit(category.get("id", ""), category.get("nodes", []))


if __name__ == "__main__":
    unittest.main()
