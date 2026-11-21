import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads((ROOT / "required-files.json").read_text(encoding="utf-8"))

    def test_every_referenced_template_exists(self):
        for section in self.inventory.get("sections", []):
            for item in section.get("items", []):
                template = item.get("template")
                if template:
                    with self.subTest(section=section["id"], template=template):
                        self.assertTrue(
                            (ROOT / "GerekliDosyalar" / "Sablonlar" / template).is_file(),
                            f"Şablon bulunamadı: {template}",
                        )

    def test_every_completed_record_points_to_an_existing_file(self):
        for section in self.inventory.get("sections", []):
            for record in section.get("completed", []):
                with self.subTest(section=section["id"], record=record["title"]):
                    self.assertEqual(record.get("status"), "YAYINDA")
                    self.assertTrue(
                        (ROOT / record["path"]).is_file(),
                        f"Tamamlandı olarak işaretlenen dosya bulunamadı: {record['path']}",
                    )

    def test_open_items_have_author_guidance(self):
        for section in self.inventory.get("sections", []):
            for item in section.get("items", []):
                with self.subTest(section=section["id"], item=item["title"]):
                    self.assertTrue(item.get("path"))
                    self.assertTrue(item.get("why"))
                    self.assertIsInstance(item.get("fields"), list)
                    self.assertGreater(len(item["fields"]), 0)

    def test_every_archive_section_has_progress_fields(self):
        for section in self.inventory.get("sections", []):
            with self.subTest(section=section["id"]):
                self.assertIn("state", section)
                self.assertIn("completed", section)
                self.assertIn("items", section)


if __name__ == "__main__":
    unittest.main()
