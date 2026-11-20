import tempfile
import unittest
from pathlib import Path

from scripts.import_obsidian import read_public_archive_note, scan_public_archive_nodes


class PublicArchiveImportTests(unittest.TestCase):
    def write_note(self, root: Path, relative: str, metadata: str, body: str = "# Kayıt\n\nAçıklama."):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + metadata.strip() + "\n---\n\n" + body + "\n", encoding="utf-8")
        return path

    def test_approved_public_note_is_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = self.write_note(root, "public.md", """
title: Public record
status: onaylandı
visibility: public
date: 1985
summary: Public summary.
order: 1
""")
            doc = read_public_archive_note(note, root)
            self.assertIsNotNone(doc)
            self.assertEqual(doc["title"], "Public record")
            self.assertEqual(doc["date"], "1985")

    def test_missing_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = self.write_note(root, "missing-status.md", """
title: Missing status
visibility: public
""")
            self.assertIsNone(read_public_archive_note(note, root))

    def test_internal_visibility_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = self.write_note(root, "internal.md", """
title: Internal
status: approved
visibility: internal
""")
            self.assertIsNone(read_public_archive_note(note, root))

    def test_draft_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = self.write_note(root, "draft.md", """
title: Draft
status: taslak
visibility: public
""")
            self.assertIsNone(read_public_archive_note(note, root))

    def test_nested_index_preserves_only_approved_children(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_note(root, "1938/index.md", """
title: 1938 — Dönem kaydı
status: approved
visibility: public
date: 1938
order: 1
""")
            self.write_note(root, "1938/event.md", """
title: Açık olay
status: approved
visibility: public
date: 10 Kasım 1938
order: 1
""")
            self.write_note(root, "1938/draft.md", """
title: Gizli taslak
status: draft
visibility: public
""")
            nodes = scan_public_archive_nodes(root, root, "chronology")
            self.assertEqual(len(nodes), 1)
            self.assertEqual(nodes[0]["title"], "1938 — Dönem kaydı")
            self.assertEqual([child["title"] for child in nodes[0]["children"]], ["Açık olay"])


if __name__ == "__main__":
    unittest.main()
