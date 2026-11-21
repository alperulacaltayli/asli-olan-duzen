from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_obsidian  # noqa: E402


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


class ArchiveCountryClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = import_obsidian.discover_archives()
        cls.categories = {item["id"]: item for item in payload["categories"]}

    def test_requested_archive_units_exist(self):
        expected = {
            "institutions", "technology", "characters",
            "society", "media", "documents",
        }
        self.assertTrue(expected.issubset(self.categories))

    def test_every_existing_leaf_record_has_a_country(self):
        for category_id in (
            "institutions", "technology", "characters",
            "society", "media", "documents",
        ):
            category = self.categories[category_id]
            leaves = [node for node in walk(category["nodes"]) if not node.get("children")]
            for node in leaves:
                with self.subTest(category=category_id, title=node["title"]):
                    self.assertIn(node.get("country"), {"turkish", "german", "both"})

    def test_kanat_and_international_press_are_shared(self):
        society_records = list(walk(self.categories["society"]["nodes"]))
        kanat = next(node for node in society_records if "Kanat Sistemi" in node["title"])
        self.assertEqual(kanat["country"], "both")

        press_records = list(walk(self.categories["media"]["nodes"]))
        self.assertEqual(len(press_records), 1)
        self.assertEqual(press_records[0]["country"], "both")

    def test_current_turkish_records_are_tagged_turkish(self):
        for category_id in ("institutions", "technology", "characters"):
            leaves = [node for node in walk(self.categories[category_id]["nodes"]) if not node.get("children")]
            self.assertTrue(leaves, category_id)
            self.assertTrue(all(node["country"] == "turkish" for node in leaves), category_id)

    def test_country_aliases_normalize(self):
        self.assertEqual(import_obsidian.normalize_country("Türkiye"), "turkish")
        self.assertEqual(import_obsidian.normalize_country("Alman"), "german")
        self.assertEqual(import_obsidian.normalize_country("Ortak"), "both")


if __name__ == "__main__":
    unittest.main()
